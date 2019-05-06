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


def fatal_code(e):
    """
    Only give up on non-429 status codes, otherwise re-try call w/ backoff
    See also: https://github.com/litl/backoff
    :param e: Exception object
    :type e: object
    :return: True if the status code is != 429, otherwise false
    :rtype: bool
    """
    return e.response.status_code not in [409, 429]

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
        # setup backoff logger
        logging.getLogger('backoff').addHandler(logging.StreamHandler())
        logging.getLogger('backoff').setLevel(log_level)

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

    def get_album_id(self, album_title, page_size=50):
        """
        Given an album title find the album or prompt the user to create one
        See also: https://developers.google.com/photos/library/reference/rest/v1/albums/list
        :param album_title: The title of the album
        :type album_title: basestring
        :param page_size: The number of results to return in pagination
        :type page_size: int
        :return: Album ID
        :rtype: basestring
        """
        resp = self.authed_session.get('https://photoslibrary.googleapis.com/v1/albums', params={'pageSize': page_size})
        resp.raise_for_status()
        for album in resp.json().get('albums',[]):
            if album.get('title') == album_title:
                self.logger.debug(f"Found {album_title}, ID: {album['id']}")
                return album['id']
        while resp.json().get('nextPageToken'):
            self.logger.debug(f"nextPageToken: {resp.json().get('nextPageToken')}")
            resp = self.authed_session.get('https://photoslibrary.googleapis.com/v1/albums', params={'pageSize': page_size, 'pageToken': resp.json().get('nextPageToken')})
            resp.raise_for_status()
            for album in resp.json().get('albums', []):
                if album.get('title') == album_title:
                    self.logger.debug(f"Found {album_title}, ID: {album['id']}")
                    assert album.get('isWriteable', False), f"The '{album_title}' album is not writable, please choose another Album name to create a new Album"
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

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, giveup=fatal_code)  # Gracefully handle throttling
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
            self.logger.debug(resp.text)
            resp.raise_for_status()
            self.logger.debug(f"Successfully uploaded {upload_file}: {resp.text}")
            return resp.text

    def upload_files(self, files):
        """
        Given a list of files, upload the files to the Album
        :param files: List of files to upload
        :type files: list
        :return: List of Upload Tokens
        :rtype: list
        """
        upload_tokens = list()
        self.logger.info(f"Uploading {len(files)} files...")
        for upload_file in tqdm(files):
            upload_tokens.append(self.upload_file(upload_file))
        self.logger.info(f"Successfully uploaded {len(files)} files")
        return upload_tokens

    @staticmethod
    def chunks(l, n):
        """Yield successive n-sized chunks from l."""
        for i in range(0, len(l), n):
            yield l[i:i + n]

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, giveup=fatal_code)  # Gracefully handle throttling
    def add_files_to_album(self, album_title, album_id, upload_tokens, chunk_size=50):
        """
        Given an Album Title, Album ID and a list of Upload Tokens, add the files to the album
        See also: https://developers.google.com/photos/library/reference/rest/v1/mediaItems/batchCreate
        :param album_title: The title of the album to upload files to
        :type album_title: basestring
        :param album_id: The ID of the Google Photos Album
        :type album_id: basestring
        :param upload_tokens: List of upload tokens of files uploaded to Google Photos
        :type upload_tokens: list
        :param chunk_size: The size of the chunks to add files to album (max of 50)
        :type chunk_size: int
        """
        self.logger.info(f"Adding {len(upload_tokens)} files to '{album_title}' in chunks of {chunk_size}...")
        with tqdm(total=len(upload_tokens)) as pbar:
            for chunk in self.chunks(upload_tokens, chunk_size):
                data = {
                    'albumId': album_id,
                    'newMediaItems': [{
                        'simpleMediaItem': {
                            'uploadToken': upload_token
                        }
                    } for upload_token in chunk]
                }
                resp = self.authed_session.post(
                    'https://photoslibrary.googleapis.com/v1/mediaItems:batchCreate',
                    data=json.dumps(data)
                )
                self.logger.debug(resp.json())
                resp.raise_for_status()
                results = resp.json()['newMediaItemResults']
                assert len(results) == len(chunk), f"Expected to find {len(upload_tokens)} mediaItem instead found {len(results)}: {resp.json()}"
                for result in results:
                    assert result['status']['message'] == 'OK', f"Expected an 'OK' Status, instead found '{result['status']['message']}': {result}"
                self.logger.debug(f"Added {len(chunk)} files to '{album_title}'")
                pbar.update(len(chunk))
            self.logger.info(f"Successfully Added {len(upload_tokens)} files to '{album_title}'")

    def run(self, album_title, directory):
        """
        :param album_title: The title of the album to upload files to
        :type album_title: basestring
        :param directory: The path to the directory to upload files from
        :type directory: basestring
        """
        album_id = self.get_album_id(album_title)
        files = self.get_files(directory)
        upload_tokens = self.upload_files(files)
        self.add_files_to_album(album_title, album_id, upload_tokens)



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Upload Photos to Google Photos")
    parser.add_argument("-a", "--album", required=True, help="Google Photos Album")
    parser.add_argument("-d", "--directory", required=True, help="Directory to look for files to upload")
    parser.add_argument("-c", "--credentials", default="./credentials.json", help="Google Photos API Credentials File")
    parser.add_argument("-l", "--log_level", default="INFO", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help="Log level")
    pargs = parser.parse_args()
    assert os.path.isdir(pargs.directory), f"{pargs.directory} is not a Directory"

    GooglePhotosUploader(pargs.credentials, pargs.log_level).run(pargs.album, pargs.directory)
