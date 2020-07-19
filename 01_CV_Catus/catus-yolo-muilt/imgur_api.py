from imgurpython import ImgurClient

def upload_photo(image_url):
    client_id = '370480dca5f63f2'
    client_secret = '8974e1d5956ce8ffeabdd03c7b51f4e4875d33ea'
    access_token = 'bee2ed62684a1678825dbfa14c6a52947ae98213'
    refresh_token = '295eaf5bccd31b4cafc3f06c73c38ef1f196528b'

    client = ImgurClient(client_id, client_secret, access_token, refresh_token)

    album_id = 'ZrRHb71'
    config = {
        'album': album_id,
    }

    print("Uploading image... ")
    image = client.upload_from_path(image_url, config=config, anon=False)
    print("Done")    
    return image['link']

if __name__ == "__main__":
    print(upload_photo('static/test.jpg'))