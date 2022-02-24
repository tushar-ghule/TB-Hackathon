from boto3 import resource
from datetime import datetime
from typing import Dict, Iterable, Union

class CSVStream:
    def __init__(
            self,
            _type: str,
            client: 's3',
            *,
            key:str | None,
            bucket: str | None,
            chunk_size: int = 1024,
            auto_connect: bool = True,
            expression: str | None = None,
            input_serialization: Dict[str, str | bool] | None = None,
            output_serialization: Dict[str, str] | None = None,
    ) -> None:
        self.type = _type if _type in ('simple', 'select') else None
        self.client = client,
        self.key = key
        self.bucket = bucket
        self.chunk_size = chunk_size
        self.expression = expression
        self.input_serialization = {'CSV': input_serialization if input_serialization else {}}
        self.output_serialization = {'CSV': output_serialization if output_serialization else {}}
        self._stream = None
        if auto_connect:
            self.connect()

    def connect(self) -> None:
        if self.type == 'select' and (not self.input_serialization or not self.output_serialization):
            raise RuntimeError('cannot open select stream without serialization options')
        if not self.client or not self.key or not self.bucket:
            raise RuntimeError('cannot open connection with client, key, and bucket')

        s3 = resource('s3')
        if self.type == 'simple':
            res = s3.meta.client.get_object(Bucket=self.bucket, Key=self.key)        
            self._stream = res.get('Body', None)
        elif self.type == 'select':
            if not self.expression:
                raise RuntimeError('cannot select without a query expression')

            res = s3.meta.client.select_object_content(
                Bucket=self.bucket,
                Key=self.key,
                ExpressionType='SQL',
                RequestProgress={'Enabled': True},
                Expression=self.expression,
                InputSerialization=self.input_serialization,
                OutputSerialization=self.output_serialization,
            )
            self._stream = res.get('Payload', None)            

    def _iter_simple_records(self) -> Iterable[str]:
        if not self.type == 'simple':
            raise RuntimeError('must be a simple CSV stream')
        if not self._stream:
            raise RuntimeError('stream has not been initialized')
        for record in self._stream.iter_lines(chunk_size=self.chunk_size):
            decoded = record.decode('utf-8')
            if decoded == '':
                continue
            else:
                yield decoded
    
    def _iter_event_stream_records(self) -> Iterable[str]:
        if self.type != 'select':
            raise RuntimeError('must be a select CSV stream')
        if self._stream is None:
            raise RuntimeError('event stream was never initialized')
        
        tail: str | None = None
        for event in self._stream:
            data = event.get('Records', {}).get('Payload', None)
            if data is not None:
                decoded = f"{tail if tail is not None else ''}{data.decode('utf-8')}"
                tail = None
                lines = decoded.split('\n')
                for line in lines:
                    # data never contains quoted commas
                    fields = line.split(',')
                    yield line

    def iter_records(self) -> Iterable[str]:
        if self.type == 'simple':
            yield from self._iter_simple_records()
        elif self.type == 'select':
            yield from self._iter_event_stream_records()
        else:
            return None
