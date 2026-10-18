"""Native multimodal token accounting and strict independent reply validation."""
import base64
import io


class TokenAudit:
    def __init__(self, checkpoint):
        from transformers import AutoProcessor, AutoTokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(checkpoint, local_files_only=True, trust_remote_code=False)
        self.processor = AutoProcessor.from_pretrained(checkpoint, local_files_only=True, trust_remote_code=False)
        if type(self.processor).__name__ != 'Qwen3VLProcessor':
            raise ValueError('unexpected native processor')

    def __call__(self, body):
        from PIL import Image
        kwargs = body.get('chat_template_kwargs', {'enable_thinking': False})
        options = dict(add_generation_prompt=True, truncation=False, **kwargs)
        ids = self.tokenizer.apply_chat_template(body['messages'], tokenize=True, **options)
        text = self.tokenizer.apply_chat_template(body['messages'], tokenize=False, **options)
        images = []
        for message in body['messages']:
            for part in message['content'] if type(message['content']) is list else []:
                if part['type'] == 'image_url':
                    url = part['image_url']['url']
                    if not url.startswith('data:image/png;base64,'):
                        raise ValueError('nonlocal image')
                    raw = base64.b64decode(url.split(',', 1)[1], validate=True)
                    image = Image.open(io.BytesIO(raw))
                    image.load()
                    if image.size != (448, 448):
                        raise ValueError('image geometry differs')
                    images.append(image.convert('RGB'))
        if not len(images) <= 6:
            raise ValueError('image cap')
        if images:
            native = self.processor(text=[text], images=images, return_tensors='pt')
            grids = [[int(v) for v in row] for row in native['image_grid_thw']]
            placeholders = ids.count(self.tokenizer.convert_tokens_to_ids('<|image_pad|>'))
            merge = int(self.processor.image_processor.merge_size)
            manual = len(ids)-placeholders+sum(t*h*w//(merge*merge) for t, h, w in grids)
            actual = len(native['input_ids'][0])
            if placeholders != len(images) or len(grids) != len(images) or actual != manual:
                raise ValueError('native multimodal accounting differs')
        else:
            actual = len(ids)
        if actual <= 0 or actual + body['max_tokens'] > 32768:
            raise ValueError('context budget')
        return actual


def validate_reply(body, reply, expected_tokens):
    if reply.get('model') != body['model'] or len(reply.get('choices', [])) != 1:
        raise ValueError('response model/choice contract')
    choice = reply['choices'][0]
    message = choice.get('message') or {}
    content, usage = message.get('content'), reply.get('usage') or {}
    if (message.get('role') != 'assistant' or message.get('tool_calls') or
            type(content) is not str or not content.strip() or choice.get('finish_reason') not in ('stop', 'length')):
        raise ValueError('response content contract')
    for key in ('prompt_tokens', 'completion_tokens', 'total_tokens'):
        if type(usage.get(key)) is not int or usage[key] <= 0:
            raise ValueError('response token type/bounds')
    if (usage['prompt_tokens'] != expected_tokens or usage['completion_tokens'] > body['max_tokens'] or
            usage['total_tokens'] != usage['prompt_tokens'] + usage['completion_tokens']):
        raise ValueError('native/server token counts differ or completion cap exceeded')
    return content
