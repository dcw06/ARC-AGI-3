"""SDK adapter. All writes are blocked except one fully validated SaveKernel."""
import json
import os
from pathlib import Path
from urllib.parse import urlparse

from . import operations as G


def serialize(package, book):
    # These SDK type modules do not authenticate or make network calls.
    from kagglesdk.kernels.types.kernels_api_service import ApiSaveKernelRequest
    from kagglesdk.kernels.types.kernels_enums import KernelExecutionType
    request = ApiSaveKernelRequest()
    for key, value in G.load(Path(package)/'launch-spec.json')['save_fields'].items():
        setattr(request, key, value)
    request.text = json.dumps(book)
    request.kernel_execution_type = KernelExecutionType.SAVE_AND_RUN_ALL
    return request, json.loads(request.to_json())


class Backend:
    READS = {'IntrospectToken', 'ListKernels', 'GetDataset', 'GetDatasetMetadata', 'GetDatasetStatus',
             'ListDatasetFiles', 'GetAcceleratorQuotaStatistics', 'GetKernel', 'GetKernelSessionStatus'}

    def __init__(self, operator, token_file, *, allow_save=False):
        import requests
        self.operator, self.allow_save = operator, allow_save
        self.original = requests.Session.send
        self.previous_token = os.environ.get('KAGGLE_API_TOKEN')
        self.installed_send = lambda session, request, **kwargs: self.send(session, request, **kwargs)
        requests.Session.send = self.installed_send
        try:
            os.environ['KAGGLE_API_TOKEN'] = Path(token_file).read_text().strip()
            from kaggle import api
            api.with_retry = lambda function, *args, **kwargs: function
            self.api = api
        except BaseException:
            self.close()
            raise

    def close(self):
        import requests
        requests.Session.send = self.original
        if self.previous_token is None:
            os.environ.pop('KAGGLE_API_TOKEN', None)
        else:
            os.environ['KAGGLE_API_TOKEN'] = self.previous_token

    def send(self, session, request, **kwargs):
        from urllib3.util.retry import Retry
        url = urlparse(request.url)
        rpc = url.path.rsplit('/', 1)[-1]
        G.require(url.scheme == 'https' and url.hostname in {'www.kaggle.com', 'api.kaggle.com'}
                  and request.method == 'POST', 'unapproved provider transport')
        G.require(rpc in self.READS or (rpc == 'SaveKernel' and self.allow_save), 'unapproved endpoint/write')
        for adapter in session.adapters.values():
            adapter.max_retries = Retry(total=0, connect=0, read=0, status=0, redirect=0)
        kwargs.update(timeout=(15, 60), allow_redirects=False)
        event = {'rpc': rpc, 'requested_at_utc': G.stamp()}
        self.operator.http_events.append(event)
        if rpc == 'SaveKernel':
            raw = request.body.encode() if isinstance(request.body, str) else request.body
            self.operator.before_send(json.loads(raw), raw)
        try:
            response = self.original(session, request, **kwargs)
            event['status'] = response.status_code
            return response
        except BaseException as error:
            event['error_type'] = type(error).__name__
            raise

    def account(self):
        return self.api.config_values.get(self.api.CONFIG_NAME_USER)

    def quota(self):
        quota = self.api.quota_view().gpu_quota
        return {key: getattr(quota, key).total_seconds() for key in ('time_used', 'time_reserved', 'total_time_allowed')}

    def own_kernels(self, owner):
        refs = set()
        for page in range(1, 21):
            rows = self.api.kernels_list(mine=True, user=owner, page=page, page_size=100)
            G.require(rows is not None, 'owner catalogue unavailable')
            if not rows:
                return refs
            for row in rows:
                ref = row.ref.strip('/').removeprefix('code/')
                # ListKernels can repeat an identity; absence needs the union of
                # every page, not a uniqueness assumption about individual rows.
                refs.add(ref)
        raise ValueError('owner catalogue pagination incomplete')

    def dataset(self, item):
        from kagglesdk.datasets.types.dataset_api_service import ApiGetDatasetRequest, ApiGetDatasetMetadataRequest
        request = ApiGetDatasetRequest()
        request.owner_slug, request.dataset_slug = item['ref'].split('/')
        with self.api.build_kaggle_client() as client:
            current = client.datasets.dataset_api_client.get_dataset(request)
        facts = {'ref': current.ref.strip('/').removeprefix('datasets/'), 'version': current.current_version_number}
        if item['kind'] != 'publisher_wheels':
            request = ApiGetDatasetMetadataRequest()
            request.owner_slug, request.dataset_slug = item['ref'].split('/')
            with self.api.build_kaggle_client() as client:
                metadata = client.datasets.dataset_api_client.get_dataset_metadata(request)
            G.require(not metadata.error_message, 'private metadata unavailable')
            facts.update(private=current.is_private is True and metadata.info.is_private is True,
                         ready=self.api.dataset_status(item['ref']) == 'ready', collaborators=len(metadata.info.collaborators))
        files, token = {}, None
        for _ in range(10):
            listing = self.api.dataset_list_files(item['ref']+'/'+str(item['version']), page_size=100, page_token=token)
            G.require(not listing.error_message, 'dataset listing unavailable')
            for row in listing.dataset_files:
                G.require(row.name not in files, 'duplicate dataset filename')
                files[row.name] = row.total_bytes
            token = listing.next_page_token
            if not token:
                return facts, files
        raise ValueError('dataset pagination incomplete')

    def save(self, request):
        with self.api.build_kaggle_client() as client:
            response = client.kernels.kernels_api_client.save_kernel(request)
        return {'ref': response.ref, 'url': response.url, 'version': response.version_number,
                'error': bool(response.error), 'invalid_sources': {name: getattr(response, name) for name in (
                    'invalid_dataset_sources', 'invalid_competition_sources', 'invalid_kernel_sources', 'invalid_model_sources')}}

    def saved(self, target):
        from kagglesdk.kernels.types.kernels_api_service import ApiGetKernelRequest
        request = ApiGetKernelRequest()
        request.user_name, request.kernel_slug = target.split('/')
        with self.api.build_kaggle_client() as client:
            response = client.kernels.kernels_api_client.get_kernel(request)
        names = ('ref', 'current_version_number', 'is_private', 'enable_gpu', 'enable_tpu', 'enable_internet',
                 'machine_shape', 'docker_image', 'dataset_data_sources', 'competition_data_sources',
                 'kernel_data_sources', 'model_data_sources')
        return {'metadata': {name: getattr(response.metadata, name) for name in names}, 'source': response.blob.source}
