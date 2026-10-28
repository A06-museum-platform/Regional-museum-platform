"""Cover selection changes only one record and immediately affects public output."""
from tests.integration.conftest import db_query


def test_cover_switch_preserves_owners_and_public_output(client, login):
    staff = login('staff@museum.org')
    exhibitions = client.get('/api/staff/exhibitions', headers=staff).json()['items']
    first, second = [e for e in exhibitions if e['status'] == 'published'][:2]
    def upload(owner, filename):
        result = client.post(f"/api/staff/exhibitions/{owner}/media", headers=staff,
                             files={'file': (filename, b'fixture image', 'image/jpeg')})
        assert result.status_code == 201, result.text
        return result.json()['media']
    a = upload(first['id'], 'a.jpg')
    b = upload(first['id'], 'b.jpeg')
    other = upload(second['id'], 'other.jpg')
    assert client.patch(f"/api/staff/media/{other['media_id']}/primary", headers=staff).status_code == 200
    result = client.patch(f"/api/staff/media/{b['media_id']}/primary", headers=staff)
    assert result.status_code == 200, result.text
    assert result.json()['is_primary'] is True
    assert result.json()['exhibition_id'] == first['id']
    assert client.get(f"/api/exhibitions/{first['slug']}").json()['hero_image_url'] == b['url']
    assert client.get(f"/api/exhibitions/{second['slug']}").json()['hero_image_url'] == other['url']
    assert client.patch(f"/api/staff/media/{a['media_id']}/primary", headers=staff).status_code == 200
    rows = db_query('SELECT media_id,exhibition_id,url,is_primary FROM media_asset WHERE media_id=ANY($1::int[]) ORDER BY media_id', [a['media_id'], b['media_id'], other['media_id']])
    by_id = {r['media_id']:r for r in rows}
    assert by_id[a['media_id']]['is_primary'] and not by_id[b['media_id']]['is_primary']
    assert by_id[other['media_id']]['is_primary']
    assert by_id[b['media_id']]['url'] == b['url']
    assert by_id[b['media_id']]['exhibition_id'] == first['id']


def test_cover_rejects_missing_video_and_unprivileged_users(client, login):
    staff = login('staff@museum.org')
    owner = client.get('/api/staff/exhibitions', headers=staff).json()['items'][0]['id']
    video = client.post(f'/api/staff/exhibitions/{owner}/media', headers=staff,
                        files={'file': ('clip.mp4', b'fixture video', 'video/mp4')}).json()['media']
    path = f"/api/staff/media/{video['media_id']}/primary"
    assert client.patch(path).status_code == 401
    for email in ['alice@example.com', 'ben@example.com']:
        assert client.patch(path, headers=login(email)).status_code == 403
    assert client.patch(path, headers=staff).status_code == 400
    assert client.patch('/api/staff/media/999999/primary', headers=staff).status_code == 404
    admin = login('admin@museum.org')
    image = client.post(f'/api/staff/exhibitions/{owner}/media', headers=admin,
                        files={'file': ('a.jpg', b'image', 'image/jpeg')}).json()['media']
    assert client.patch(f"/api/staff/media/{image['media_id']}/primary", headers=admin).status_code == 200
