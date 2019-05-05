# google-photos-uploader

Python based uploader for uploading files to [Google Photos](https://photos.google.com/) from the commandline.
This script has been tested uploading a directory with over 5000 images in it.

## Setup

1. Install requirements: `pip install -r requirements.txt`
2. Signup for an Google Photos API here: https://developers.google.com/photos/library/guides/get-started
![enable api key screenshot](assets/enable_api_key.png)
3. Download the `credentials.json` file and place it in this directory

## Run

1. Run `./google-photos-uploader.py -a <album_name> -d <directory_to_upload_files_from>`
2. You will be prompted with the following:
```bash
Please visit this URL to authorize this application: https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=<your_client_id>&redirect_uri=urn%3Aietf%3Awg%3Aoauth%3A2.0%3Aoob&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fphotoslibrary&state=<custom_state>&prompt=consent&access_type=offline
Enter the authorization code:
```
3. Enter in your authorization code.

Note: If the album doesn't exist this script will create it for you.

## TODOs

- Provide caching of credentials so you don't need to re-authenticate on every run
- Add Travis CI
    - Add linting
    - Add tests
- Add coverage reports (https://coveralls.io)

## License

GNU GENERAL PUBLIC LICENSE v3 - See the [LICENSE](LICENSE) file for more information
