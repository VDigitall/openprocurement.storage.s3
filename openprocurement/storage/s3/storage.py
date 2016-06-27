from email.header import decode_header
from openprocurement.documentservice.storage import StorageRedirect, MD5Invalid, KeyNotFound, get_filename
from rfc6266 import build_header
from urllib import quote
from uuid import uuid4, UUID


class S3Storage:
    connection = None
    bucket = None

    def __init__(self, connection, bucket):
        self.connection = connection
        self.bucket = bucket

    def register(self, md5):
        bucket = self.connection.get_bucket(self.bucket)
        uuid = uuid4().hex
        path = '/'.join([format(i, 'x') for i in UUID(uuid).fields])
        key = bucket.new_key(path)
        key.set_metadata('md5', md5)
        key.set_contents_from_string('')
        key.set_acl('private')
        return uuid

    def upload(self, post_file, uuid=None):
        filename = get_filename(post_file.filename)
        content_type = post_file.type
        in_file = post_file.file
        bucket = self.connection.get_bucket(self.bucket)
        if uuid is None:
            uuid = uuid4().hex
            path = '/'.join([format(i, 'x') for i in UUID(uuid).fields])
            key = bucket.new_key(path)
        else:
            try:
                path = '/'.join([format(i, 'x') for i in UUID(uuid).fields])
            except ValueError:
                raise KeyNotFound(uuid)
            if path not in bucket:
                raise KeyNotFound(uuid)
            key = bucket.get_key(path)
            md5 = key.get_metadata('md5')
            if key.compute_md5(in_file)[0] != md5:
                raise MD5Invalid
        key.set_metadata('Content-Type', content_type)
        key.set_metadata("Content-Disposition", build_header(filename, filename_compat=quote(filename.encode('utf-8'))))
        key.set_contents_from_file(in_file)
        key.set_acl('private')
        return uuid, key.etag[1:-1], content_type, filename

    def get(self, uuid):
        if '/' in uuid:
            path = uuid
        else:
            try:
                UUID(uuid)
            except ValueError:
                raise KeyNotFound(uuid)
            path = '/'.join([format(i, 'x') for i in UUID(uuid).fields])
        url = self.connection.generate_url(method='GET', bucket=self.bucket, key=path, expires_in=300)
        raise StorageRedirect(url)
