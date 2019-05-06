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
3. Visit the provided URL and agree to terms:
![agree to terms](assets/agree_to_terms.png)
4. Copy the authorization code from the following page:
![copy code](assets/copy_code.png)
5. Enter in your authorization code in the terminal and hit enter.

Note: If the album doesn't exist this script will create it for you.  If the album exists but wasn't created by this 
script it is likely not writeable and therefore the script will fail and ask you to pick another album name (see [TODOs](#todos)). 

### Example Run

```bash
$ ./uploader.py -a "My Photos" -d photos/
Please visit this URL to authorize this application: https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=<your_client_id>&redirect_uri=urn%3Aietf%3Awg%3Aoauth%3A2.0%3Aoob&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fphotoslibrary&state=<custom_state>&prompt=consent&access_type=offline
Enter the authorization code: <your_authorization_code>
Found 5442 files in photos/
Uploading 5442 files...
 41%|████▏     | 2257/5442 [07:58<10:18,  5.15it/s]
Backing off upload_file(...) for 0.6s (requests.exceptions.HTTPError: 429 Client Error: Too Many Requests for url: https://photoslibrary.googleapis.com/v1/uploads)
Backing off upload_file(...) for 0.6s (requests.exceptions.HTTPError: 429 Client Error: Too Many Requests for url: https://photoslibrary.googleapis.com/v1/uploads)
 74%|███████▍  | 4026/5442 [13:58<04:21,  5.42it/s]
Backing off upload_file(...) for 0.1s (requests.exceptions.HTTPError: 429 Client Error: Too Many Requests for url: https://photoslibrary.googleapis.com/v1/uploads)
 74%|███████▍  | 4027/5442 [13:58<05:26,  4.33it/s]
Backing off upload_file(...) for 0.7s (requests.exceptions.HTTPError: 429 Client Error: Too Many Requests for url: https://photoslibrary.googleapis.com/v1/uploads)
Backing off upload_file(...) for 1.7s (requests.exceptions.HTTPError: 429 Client Error: Too Many Requests for url: https://photoslibrary.googleapis.com/v1/uploads)
100%|██████████| 5442/5442 [18:49<00:00,  5.84it/s]
Successfully uploaded 5442 files
Adding 5442 files to 'My Photos' in chunks of 50...
100%|██████████| 5442/5442 [09:03<00:00,  9.92it/s]
Successfully Added 5442 files to 'My Photos'
```

## TODOs

- Figure out how to make existing Albums writable (see also: https://github.com/ChrisRut/google-photos-uploader/blob/456ce354a7367717da86dfb7ee82761a11bb332f/google-photos-uploader.py#L87)
- Provide caching of credentials so you don't need to re-authenticate on every run
- Add Travis CI
    - Add linting
    - Add tests
- Add coverage reports (https://coveralls.io)

## License

GNU GENERAL PUBLIC LICENSE v3 - See the [LICENSE](LICENSE) file for more information
