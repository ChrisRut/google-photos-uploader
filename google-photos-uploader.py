#!/usr/bin/env python3
"""
See: https://github.com/ChrisRut/google-photos-uploader
"""
import argparse
import backoff
import json
import logging
import os
import requests
from google.auth.transport.requests import AuthorizedSession
from google_auth_oauthlib.flow import InstalledAppFlow
from tqdm import tqdm


class GooglePhotosUploader(object):
    def __init__(self, credentials_file, log_level):
        """
        :param credentials_file: Path to Google Photos API credentials file
        :type credentials_file: basestring
        :param log_level: Log Level
        :type log_level: basestring
        """
        # create logger
        self.logger = logging.getLogger('google-photos-uploader')
        self.logger.addHandler(logging.StreamHandler())
        self.logger.setLevel(log_level)

        # Setup authenticated session
        flow = InstalledAppFlow.from_client_secrets_file(
            credentials_file,
            scopes=['https://www.googleapis.com/auth/photoslibrary']
        )
        credentials = flow.run_console()

        self.authed_session = AuthorizedSession(credentials)

    def create_album(self, album_title):
        """
        Given an album title create an album and return it's ID
        See also: https://developers.google.com/photos/library/reference/rest/v1/albums/create
        :param album_title: The title of the album
        :type album_title: basestring
        :return: Album ID
        :rtype: basestring
        """
        resp = self.authed_session.post('https://photoslibrary.googleapis.com/v1/albums', data=json.dumps({'album': {'title': album_title}}))
        self.logger.info(f"Successfully created album '{album_title}'.")
        return resp.json()['id']

    def get_album_id(self, album_title):
        """
        Given an album title find the album or prompt the user to create one
        See also: https://developers.google.com/photos/library/reference/rest/v1/albums/list
        :param album_title: The title of the album
        :type album_title: basestring
        :return: Album ID
        :rtype: basestring
        """
        resp = self.authed_session.get('https://photoslibrary.googleapis.com/v1/albums', params={'pageSize': 50})
        resp.raise_for_status()
        for album in resp.json().get('albums',[]):
            if album.get('title') == album_title:
                self.logger.debug(f"Found {album_title}, ID: {album['id']}")
                return album['id']
        while resp.json().get('nextPageToken'):
            self.logger.debug(f"nextPageToken: {resp.json().get('nextPageToken')}")
            resp = self.authed_session.get('https://photoslibrary.googleapis.com/v1/albums', params={'pageSize': 50, 'pageToken': resp.json().get('nextPageToken')})
            resp.raise_for_status()
            for album in resp.json().get('albums', []):
                if album.get('title') == album_title:
                    self.logger.debug(f"Found {album_title}, ID: {album['id']}")
                    return album['id']
        # Unable to find album, prompt the user to create it
        self.logger.warning(f"Unable to find the album '{album_title}'.")
        resp = input(f"Would you like to create {album_title} (y/n)? ")
        if resp.lower() in ['y','ye','yes']:
            return self.create_album(album_title)

    def get_files(self, directory):
        """
        Given a directory return a list of files to upload to the album
        :param directory: The path to the directory to upload files from
        :type directory: basestring
        :return: List of files to upload
        :rtype: list
        """
        files = [entry for entry in os.scandir(os.path.abspath(directory)) if entry.is_file()]
        self.logger.info(f"Found {len(files)} files in {directory}")
        return files

    def upload_file(self, upload_file):
        """
        Given file upload it to Google Photos
        See also: https://developers.google.com/photos/library/guides/upload-media#uploading-bytes
        :param upload_file: File to upload to Google Photos
        :type upload_file: basestring
        :return: UPLOAD_TOKEN
        :rtype: basestring
        """
        with open(upload_file, 'rb') as f:
            resp = self.authed_session.post(
                'https://photoslibrary.googleapis.com/v1/uploads',
                headers={
                    'Content-type': 'application/octet-stream',
                    'X-Goog-Upload-Protocol': 'raw',
                    'X-Goog-Upload-File-Name': os.path.basename(upload_file)
                },
                data=f,
            )
            if resp.status_code != 200:
                import pdb ; pdb.set_trace()
                self.logger.error(f"Failed to upload {upload_file}: {resp.json()}")
                return None
            self.logger.debug(f"Successfully uploaded {upload_file}: {resp.text}")
            return resp.text

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException)
    def add_file_to_album(self, album_id, upload_token):
        """
        Given an Album ID and Upload Token, add the file to the album
        See also: https://developers.google.com/photos/library/reference/rest/v1/mediaItems/batchCreate
        :param album_id: The ID of the Google Photos Album
        :type album_id: basestring
        :param upload_token: Upload Token of file uploaded to Google Photos
        :type upload_token: basestring
        """
        data = {
            'albumId': album_id,
            'newMediaItems': [{
                'simpleMediaItem': {
                    'uploadToken': upload_token
                }
            }]
        }
        resp = self.authed_session.post(
            'https://photoslibrary.googleapis.com/v1/mediaItems:batchCreate',
            data=json.dumps(data)
        )
        resp.raise_for_status()
        results = resp.json()['newMediaItemResults']
        assert len(results) == 1, f"Expected to find 1 mediaItem instead found {len(results)}: {resp.json()}"
        assert results[0]['status']['message'] == 'OK', f"Expected an 'OK' Status, instead found '{results[0]['status']['message']}': {resp.json()}"

    def upload_files(self, album_id, files):
        """
        Given an Album ID and list of files, upload the files to the Album
        :param album_id: The ID of the Google Photos Album
        :type album_id: basestring
        :param files: List of files to upload
        :type files: list
        """
        successfully_uploaded = 0
        error_upload = 0
        for upload_file in tqdm(files):
            upload_token = self.upload_file(upload_file)
            if upload_token:
                successfully_uploaded += 1
                self.add_file_to_album(album_id, upload_token)
            else:
                error_upload += 1
        self.logger.info(f"Successfully uploaded {successfully_uploaded} files, failed to upload {error_upload} files")

    def run(self, album_title, directory):
        """
        :param album_title: The title of the album to upload files to
        :type album_title: basestring
        :param directory: The path to the directory to upload files from
        :type directory: basestring
        """
        album_id = self.get_album_id(album_title)
        files = self.get_files(directory)
        self.upload_files(album_id, files)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Upload Photos to Google Photos")
    parser.add_argument("-a", "--album", required=True, help="Google Photos Album")
    parser.add_argument("-d", "--directory", required=True, help="Directory to look for files to upload")
    parser.add_argument("-c", "--credentials", default="./credentials.json", help="Google Photos API Credentials File")
    parser.add_argument("-l", "--log_level", default="INFO", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help="Log level")
    pargs = parser.parse_args()
    assert os.path.isdir(pargs.directory), f"{pargs.directory} is not a Directory"

    GooglePhotosUploader(pargs.credentials, pargs.log_level).run(pargs.album, pargs.directory)
