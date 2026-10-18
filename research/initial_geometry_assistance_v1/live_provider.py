"""Allowlisted Kaggle SDK adapter; zero retries and at most one guarded save."""
import json
import os
from pathlib import Path
from urllib.parse import urlparse


class Provider:
    READS = {'IntrospectToken', 'ListKernels', 'GetDataset', 'GetDatasetMetadata', 'GetDatasetStatus',
             'ListDatasetFiles', 'GetAcceleratorQuotaStatistics', 'GetKernel', 'GetKernelSessionStatus'}

    def __init__(self, token_file, *, boundary=None):
        import requests
        self.boundary = boundary
        self.original = requests.Session.send
        self.previous_token = os.environ.get('KAGGLE_API_TOKEN')
        self.events = []
        requests.Session.send = lambda session, request, **kwargs: self.send(session, request, **kwargs)
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
        if (url.scheme != 'https' or url.hostname not in {'www.kaggle.com', 'api.kaggle.com'} or
                request.method != 'POST' or (rpc not in self.READS and not (rpc == 'SaveKernel' and self.boundary))):
            raise PermissionError('provider write/endpoint not allowed')
        for adapter in session.adapters.values():
            adapter.max_retries = Retry(total=0, connect=0, read=0, status=0, redirect=0)
        kwargs.update(timeout=(15, 60), allow_redirects=False)
        event = {'rpc': rpc}
        self.events.append(event)
        if rpc == 'SaveKernel':
            raw = request.body.encode() if isinstance(request.body, str) else request.body
            self.boundary.before_send(json.loads(raw), raw)
        try:
            response = self.original(session, request, **kwargs)
            event['status'] = response.status_code
            return response
        except BaseException as exc:
            event['error_type'] = type(exc).__name__
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
            if rows is None:
                raise ValueError('owner catalogue unavailable')
            if not rows:
                return refs
            refs.update(row.ref.strip('/').removeprefix('code/') for row in rows)
        raise ValueError('owner catalogue pagination incomplete')

    def dataset(self, ref, version, *, private=False):
        from kagglesdk.datasets.types.dataset_api_service import ApiGetDatasetRequest, ApiGetDatasetMetadataRequest
        request = ApiGetDatasetRequest()
        request.owner_slug, request.dataset_slug = ref.split('/')
        with self.api.build_kaggle_client() as client:
            current = client.datasets.dataset_api_client.get_dataset(request)
        facts = {'ref': current.ref.strip('/').removeprefix('datasets/'), 'version': current.current_version_number}
        if private:
            request = ApiGetDatasetMetadataRequest()
            request.owner_slug, request.dataset_slug = ref.split('/')
            with self.api.build_kaggle_client() as client:
                metadata = client.datasets.dataset_api_client.get_dataset_metadata(request)
            if metadata.error_message:
                raise ValueError('private dataset metadata unavailable')
            facts.update(private=current.is_private is True and metadata.info.is_private is True,
                         ready=self.api.dataset_status(ref) == 'ready', collaborators=len(metadata.info.collaborators))
        files, token = {}, None
        for _ in range(10):
            listing = self.api.dataset_list_files(ref+'/'+str(version), page_size=100, page_token=token)
            if listing.error_message:
                raise ValueError('dataset listing unavailable')
            for row in listing.dataset_files:
                if row.name in files:
                    raise ValueError('duplicate dataset file')
                files[row.name] = row.total_bytes
            token = listing.next_page_token
            if not token:
                return facts, files
        raise ValueError('dataset pagination incomplete')

    def save(self, request):
        with self.api.build_kaggle_client() as client:
            response = client.kernels.kernels_api_client.save_kernel(request)
        return {'ref': response.ref, 'url': response.url, 'version': response.version_number,
                'error': bool(response.error), 'invalid_sources': {name: getattr(response, name) for name in
                ('invalid_dataset_sources', 'invalid_competition_sources', 'invalid_kernel_sources', 'invalid_model_sources')}}

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
