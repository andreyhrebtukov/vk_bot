import vk_api




def getUserId(text):
    id = text
    if 'vk.com/' in text:
        id = text.split('/')[-1]
    if not id.replace('id', '').isdigit():
        id = vk_api.utils.resolveScreenName(screen_name=id)['object_id']
    else:
        id = id.replace('id', '')
    return "id"+int(id)
