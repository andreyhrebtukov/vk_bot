import vk_api
import time
import datetime
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import test_config as config
from operator import itemgetter
import random
import shelve


# TODO -

class group_bot():
    def __init__(self):
        self.day = 86400
        self.user_commands = {
            '!чек': self.check_friends,
            '!пост': self.check_post,
            '!кик': self.delete,
            '!хелп': self.help,
            '!автопост': self.set_auto
        }
        self.group_commands = {
            '!правила': self.say_rulers,
            '!обновить': self.set_rules,
            '!макет': self.set_template,
            '!категория': self.set_categories,
            '!добавить': self.set_user_to_category,
            '!список': self.print_user_list,
            '!убрать': self.delete_user,
            '!+группа': self.add_group,
            '!-группа': self.delete_group,
            '!ключ': self.set_key,
            '!группы': self.print_group,
            '!время': self.set_time
        }
        self.vk_app_session = vk_api.VkApi(token=config.token_for_app)
        self.app_api = self.vk_app_session.get_api()
        self.vk_group_session = vk_api.VkApi(token=config.token_for_bot)
        self.group_api = self.vk_group_session.get_api()

    def set_auto(self, _, peer_id, __):
        with shelve.open('auto') as file:
            copy = file.get('list', [])
            if peer_id in copy:
                copy.remove(peer_id)
                status = 'отключен'
            else:
                copy.append(peer_id)
                status = "включен"
            file['list'] = copy
        self.group_api.messages.send(peer_id=peer_id,
                                     message="Автопостинг {}!".format(status),
                                     random_id=random.randrange(1000000))

    def help(self, _, peer_id, chat_id):
        text = """
        Привет! Здесь ты можешь ввести команды нашего бота!
        Людей можно задавать как через текстовые ники так и через id (durov/id1)
        Группы через текстовые названия или цифровые значения (vkapi/1)
        Команды могут использовать ТОЛЬКО АДМИНИСТРАТОРЫ чата.
        '!чек' id123 - проверка, что юзер добавил всех в чате в друзья.
        '!пост' - проверка количества постов. Делаем раз в час, чаще не даст!
        '!кик' id123 - Удаляет юзера
        '!хелп' - Ну это, вы сейчас тут.
        '!правила' - Выводит правила (если вы их задали)
        '!обновить' text - Задает правила
        '!макет' - Задает шаблон сообщения для юзеров. Для задания места для категории пишите Категория*, где
        * - номер категории. Для юзеров пишите Юзеры*, где * - номер категории. Отсчет категорий идет с 0 Пример
        ТЕКСТ
        ---Категория0---
        ===Юзеры0===
        '!категория' cat1 cat2 cat3... - назначает категории. Их должно быть столько же, сколько вы задали в шаблоне!
        '!добавить' cat_name user - добавляет 1 юзера в выбранную категорию.
        '!список' - вывести список юзеров по категориям
        '!убрать' - удаляет юзеров из списка
        '!+группа' vkapi, 213123 - добавляет группы в список поиска для метода !пост
        '!-группа' - удаляет группы со списка.
        '!группы' - выводит список добавленных групп.
        '!ключ' - задает ключевое слово поиска в группах для метода !пост
        """
        self.group_api.messages.send(peer_id=peer_id, message=text,
                                     random_id=random.randrange(1000000))

    def parse_group(self, group, peer_id):
        index = 0
        posts = []
        flag = True
        t = datetime.datetime.now()
        with shelve.open('time') as file:
            time = [int(x) for x in file.get(str(peer_id), [0, 0])]
        if t.hour >= time[0] and t.minute >= time[1]:
            c = datetime.datetime(t.year, t.month, t.day, hour=time[0], minute=time[1], second=0, microsecond=0)
        else:
            c = datetime.datetime(t.year, t.month, t.day, hour=time[0], minute=time[1], second=0, microsecond=0) \
                - datetime.timedelta(days=1)
        t = datetime.datetime.timestamp(c)
        while flag:
            try:
                with shelve.open('keys') as file:
                    try:
                        key = file[str(peer_id)]
                    except Exception:
                        self.group_api.messages.send(peer_id=peer_id,
                                                     message="Ключевое слово не добавлено! Вопспользуйтесь командой !ключ, чтобы его добавить.",
                                                     random_id=random.randrange(1000000))
                    else:
                        temp = self.app_api.wall.search(owner_id=group, query=key, owners_only=0, count=100,
                                                        offset=index * 100, extended=0)
            except Exception as err:
                print(err)
                return []
            index += 1
            if temp['items']:
                if temp['count'] < 100 or (t > int(temp['items'][-1]['date'])):
                    flag = False
                for elem in temp['items']:
                    if t < int(elem['date']):
                        b = datetime.datetime.fromtimestamp(t)
                        b = datetime.datetime.strftime(b, "%D   %H:%M:%S")
                        a = datetime.datetime.fromtimestamp(elem['date'])
                        a = datetime.datetime.strftime(a, "%D   %H:%M:%S")
                        print('t = ' + str(b) + "    " + 'b = ' + str(a))
                        posts.append(elem['from_id'])
            else:
                flag = False
        return posts

    def check_post(self, cmd, chat_peer, chat_id):
        """
        d = shelve.open('shelve')
        try:
            time_last_start = d[str(chat_peer)]
        except Exception as err:
            time_last_start = 1
            print(err)
        time_now = time.time()
        d.close()
        if time_now - time_last_start < 3600:
            t = time.strftime('%H:%M:%S', time.gmtime(3600 - (time_now - time_last_start)))
            self.group_api.messages.send(peer_id=chat_peer,
                                         message="Воу-воу! Еще рано. Еще {t} до запуска!!".format(t=t),
                                         random_id=random.randrange(1000000))
            print(time_now - time_last_start)
            return 0
        else:
        """
        if True:
            d = shelve.open('shelve')
            d[str(chat_peer)] = time.time()
            d.close()
            # print(time_now - time_last_start)
            users_in_chat = []
            dict_name_users = {}
            temp = [user for user in
                    self.group_api.messages.getConversationMembers(peer_id=chat_peer, fields='first_name')['profiles']]

            for i in temp:
                users_in_chat.append(i['id'])
                dict_name_users[i['id']] = i['first_name'] + " " + i['last_name']
            dict_users = {}
            for user in users_in_chat:
                dict_users[user] = 0
            with shelve.open('clubs') as file:
                try:
                    groups = file[str(chat_peer)]
                except Exception:
                    self.group_api.messages.send(peer_id=chat_peer,
                                                 message="Группы не назначены. "
                                                         "Воспользуйтесь командой"
                                                         " !+группа, чтобы добавить группы",
                                                 random_id=random.randrange(1000000))
            for group in groups:
                posts = self.parse_group(group, chat_peer)
                for i in posts:
                    if i in dict_users:
                        dict_users[i] += 1
            users_in_chat = sorted(dict_users.items(), key=itemgetter(1))
            users_in_chat.reverse()
            text = "Было создано постов: \n"
            text += "_____________________\n"
            num = 1
            for user in users_in_chat:
                text += str(num) + '. @id' + str(user[0]) + " " + dict_name_users[user[0]] + ': ' + str(user[1]) + '\n'
                num += 1
            text += "_____________________"
            self.group_api.messages.send(peer_id=chat_peer, message=text, random_id=random.randrange(1000000))

    def get_followers(self, user_id):
        index = 0
        list_followers = []
        flag = True
        while flag:
            temp = self.app_api.users.getFollowers(user_id=user_id, offset=index * 1000, count=1000)
            index += 1
            if len(temp) < 1000:
                flag = False
            for elem in temp['items']:
                list_followers.append(elem)
        return list_followers

    def check_friends(self, users, chat_peer, chat_id):
        user_in_chat_ids = self.get_users_in_chat(chat_peer)
        for user in users:
            try:
                user_friends_list = self.app_api.friends.get(user_id=user, count=18000)
            except Exception as err:
                if 'private' in err.error['error_msg']:
                    self.group_api.messages.send(peer_id=chat_peer, message=f"@id{user} - приватный аккаунт!",
                                                 random_id=random.randint(0, 10000000))
            else:
                info = {'friends': 0, 'followers': 0, 'not_friends': []}
                for group_user in user_in_chat_ids:
                    if group_user['id'] != user:
                        try:
                            user_followers_list = self.get_followers(group_user['id'])
                        except Exception as err:
                            if 'private' in err.error['error_msg']:
                                self.group_api.messages.send(peer_id=chat_peer,
                                                             message=f"@id{group_user['id']} - приватный аккаунт!",
                                                             random_id=random.randint(0, 10000000))
                        else:
                            if group_user['id'] in user_friends_list['items']:
                                info['friends'] += 1
                            elif user in user_followers_list:
                                info['followers'] += 1
                            else:
                                info['not_friends'].append(group_user)
                non_friend_text = ''
                count = 1
                for user in info['not_friends']:
                    non_friend_text += f'{count}. {user["first_name"]} {user["last_name"]} vk.com/id{user["id"]}\n'
                    count += 1
                self.group_api.messages.send(peer_id=chat_peer,
                                             message=f"1.&#128018;Есть в друзьях: {info['friends']}\n"
                                             f"2.&#128585;Есть в подписчиках: {info['followers']}\n"
                                             f"3.&#128584;Не добавлено: {len(info['not_friends'])}\n"
                                             "\n"
                                             f"{non_friend_text}",
                                             random_id=random.randrange(100000))

    def delete(self, users, peer_id, chat_id):
        # Тоже надо проверить
        user_in_chat_ids = self.get_users_in_chat(peer_id)
        for user in users:
            try:
                self.group_api.messages.removeChatUser(chat_id=chat_id, user_id=user)
            except Exception:
                self.group_api.messages.send(peer_id=peer_id,
                                             message="Не получилось удалить юзера (МИСТИКА КАКАЯ-ТО)!",
                                             random_id=random.randrange(1000000))
            else:
                self.delete_user(f"id{user}", peer_id)
        self.print_user_list(None, peer_id)

    def admin_list(self, peer_id):
        users = self.group_api.messages.getConversationMembers(peer_id=peer_id)['items']
        admin_list = []
        for user in users:
            if user.get('is_admin'):
                admin_list.append(user['member_id'])
        return admin_list

    # Списки групп
    def add_group(self, groups, peer_id):
        group_list = self.group_api.groups.getById(group_ids=groups)
        with shelve.open('clubs') as file:
            try:
                copy = file[str(peer_id)]
            except Exception:
                copy = []

            for group in group_list:
                if group['id'] not in copy:
                    copy.append(group['id'] * -1)
            file[str(peer_id)] = copy
        self.group_api.messages.send(peer_id=peer_id,
                                     message="Группы добавлены!",
                                     random_id=random.randrange(1000000))

    def delete_group(self, groups, peer_id):
        group_list = self.group_api.groups.getById(group_ids=groups)
        with shelve.open('clubs') as file:
            try:
                copy = file[str(peer_id)]
            except Exception:
                self.group_api.messages.send(peer_id=peer_id,
                                             message="Группы не назначены!",
                                             random_id=random.randrange(1000000))
            else:
                for group in group_list:
                    if -1 * group['id'] in copy:
                        copy.remove(group['id'] * -1)
                file[str(peer_id)] = copy
                self.group_api.messages.send(peer_id=peer_id,
                                             message="Группы удалены!",
                                             random_id=random.randrange(1000000))

    def print_group(self, _, peer_id):
        with shelve.open('clubs') as file:
            try:
                copy = file[str(peer_id)]
                find = [str(-1 * gr) for gr in copy]
                group_list = self.group_api.groups.getById(group_ids=','.join(find))
                text = 'Группы:\n'
                for group in group_list:
                    text += f'vk.com/club{group["id"]}\n'
                self.group_api.messages.send(peer_id=peer_id,
                                             message=text,
                                             random_id=random.randrange(1000000))
            except Exception:
                self.group_api.messages.send(peer_id=peer_id,
                                             message="Группы не назначены!",
                                             random_id=random.randrange(1000000))

    # Ключевое слово

    def set_key(self, key, peer_id):
        with shelve.open('keys') as file:
            file[str(peer_id)] = key
            self.group_api.messages.send(peer_id=peer_id,
                                         message="Ключевое слово добавлено!",
                                         random_id=random.randrange(1000000))

    def set_time(self, time, peer_id):
        with shelve.open('time') as file:
            file[str(peer_id)] = time.split('.')
            self.group_api.messages.send(peer_id=peer_id,
                                         message="Время назначено!",
                                         random_id=random.randrange(1000000))

    # ПРАВИЛА

    def set_rules(self, rules_text, peer_id):
        with shelve.open('rules') as file:
            file[str(peer_id)] = rules_text
        self.group_api.messages.send(peer_id=peer_id,
                                     message="Правила назначены! Для показа используйте команду !правила",
                                     random_id=random.randrange(1000000))

    def say_rulers(self, _, peer_id):
        with shelve.open('rules') as file:
            try:
                self.group_api.messages.send(peer_id=peer_id, message=file[str(peer_id)],
                                             random_id=random.randrange(1000000))
            except Exception as err:
                self.group_api.messages.send(peer_id=peer_id, message="А правил-то и нет! ГУЛЯЕМ! "
                                                                      "Или задайте правила командой !обновить",
                                             random_id=random.randrange(1000000))

    # ________________________________
    # Лист пользователей
    def set_template(self, template, peer_id):
        with shelve.open('templates') as file:
            file[str(peer_id)] = template
        self.group_api.messages.send(peer_id=peer_id,
                                     message="Шаблон назначен!",
                                     random_id=random.randrange(1000000))

    def set_categories(self, text, peer_id):
        categories = text.split(' ')
        with shelve.open('templates') as file:
            template = file[str(peer_id)]
        count_cat = template.count('Категория')
        if len(categories) != count_cat:
            self.group_api.messages.send(peer_id=peer_id, message='Введено неверное количество категорий!',
                                         random_id=random.randrange(1000000))
        else:
            with shelve.open('categories') as file:
                user_list = [{cat: []} for cat in categories]
                file[str(peer_id)] = user_list
                self.group_api.messages.send(peer_id=peer_id,
                                             message="Категории назначены!",
                                             random_id=random.randrange(1000000))

    def set_user_to_category(self, text, peer_id):
        category = text.split(' ')[0]
        user_list = text.split(' ')[1:]
        with shelve.open('categories') as file:
            copy = file[str(peer_id)]
            new_user = self.get_users_id_from_nicknames(user_list)[0]
            for cat in copy:
                if category in cat.keys():
                    try:
                        if new_user not in cat[category]:
                            cat[category].append(new_user)
                            self.group_api.messages.send(peer_id=peer_id,
                                                         message=f"Юзер @id{new_user} добавлен в категорию {category}",
                                                         random_id=random.randrange(1000000))
                    except Exception:
                        self.group_api.messages.send(peer_id=peer_id,
                                                     message="Категории не заданы! Воспользуйтесь командой "
                                                             "!категория для задания категорий",
                                                     random_id=random.randrange(1000000))
                else:
                    try:
                        cat[list(cat.keys())[0]].remove(new_user)
                        self.group_api.messages.send(peer_id=peer_id,
                                                     message=f"Юзер @id{new_user} удален из категории {category}",
                                                     random_id=random.randrange(1000000))
                    except ValueError:
                        pass
            file[str(peer_id)] = copy

    def delete_user(self, text, peer_id):
        user_list = text.split(' ')
        with shelve.open('categories') as file:
            try:
                copy = file[str(peer_id)]
            except Exception:
                self.group_api.messages.send(peer_id=peer_id,
                                             message="Категории не назначены. Назначьте их с помощью команды !категория",
                                             random_id=random.randrange(1000000))
            new_user = self.get_users_id_from_nicknames(user_list)
            for user in new_user:
                for cat in copy:
                    try:
                        cat[list(cat.keys())[0]].remove(user)
                        self.group_api.messages.send(peer_id=peer_id,
                                                     message=f"Юзер @id{user} удален из категории "
                                                     f"{list(cat.keys())[0]}",
                                                     random_id=random.randrange(1000000))
                    except ValueError:
                        pass
            file[str(peer_id)] = copy

    def print_user_list(self, _, peer_id):
        text = ''
        with shelve.open('templates') as file:
            try:
                text = file[str(peer_id)]
            except Exception:
                self.group_api.messages.send(peer_id=peer_id,
                                             message="Шаблон не задан! Воспользуйтесь командой "
                                                     "!макет для задания категорий",
                                             random_id=random.randrange(1000000))
        with shelve.open('categories') as file:
            try:
                categories = file[str(peer_id)]
            except Exception:
                self.group_api.messages.send(peer_id=peer_id,
                                             message="Категории не заданы! Воспользуйтесь командой "
                                                     "!set_categories для задания категорий",
                                             random_id=random.randrange(1000000))
            else:
                final_text = ''
                text_list = text.split('\n')
                for line in text_list:
                    if 'Категория' in line:
                        index_of_cat = line[line.index('Категория') + 9]
                        cat_name = self.get_cat_name(categories, index_of_cat)
                        line = line.replace('Категория' + index_of_cat, cat_name)
                        final_text += line
                    elif 'Юзеры' in line:
                        user_replace_text = ''
                        index_of_cat = line[line.index('Юзеры') + 5]
                        users = list(categories[int(index_of_cat)].values())[0]
                        if len(users) != 0:
                            for user in users:
                                user_info = self.app_api.users.get(user_id=user)[0]
                                user_replace_text += line.replace('Юзеры' + index_of_cat,
                                                                  f' @id{user_info["id"]} {user_info["first_name"]} '
                                                                  f'{user_info["last_name"]}\n')
                            user_replace_text = user_replace_text[:-2]
                        else:
                            user_replace_text += line.replace('Юзеры' + index_of_cat, "Cвободное место")
                        line = line.replace(line, user_replace_text)
                        final_text += line
                    else:
                        final_text += line
                    final_text += '\n'
            self.group_api.messages.send(peer_id=peer_id, message=final_text,
                                         random_id=random.randrange(1000000))

    def add_user_to_list(self, id, peer_id):
        with shelve.open('categories') as file:
            try:
                cat_name = self.get_cat_name(file[str(peer_id)], len(file[str(peer_id)]) - 1)
                self.set_user_to_category(f'{cat_name} {str(id)}', peer_id)
            except Exception:
                self.group_api.messages.send(peer_id=peer_id,
                                             message="Категории не заданы! Воспользуйтесь командой "
                                                     "!категория для задания категорий",
                                             random_id=random.randrange(1000000))

    def get_users_id_from_nicknames(self, nicknames):
        return [user['id'] for user in self.group_api.users.get(user_ids=','.join(map(str, nicknames)))]

    def get_cat_name(self, cat_dict, index_of_cat):
        return list(cat_dict[int(index_of_cat)].keys())[0]

    def get_users_in_chat(self, peer_id):
        temp = self.group_api.messages.getConversationMembers(peer_id=peer_id, fields='id')
        members_id = [user['member_id'] for user in temp['items']]
        result = []
        for man in temp['profiles']:
            if man['id'] in members_id and not man.get('deactivated'):
                result.append(man)
        return result

    # _________________________________________

    def main(self):
        longpoll = VkBotLongPoll(self.vk_group_session, config.bot_id)
        for event in longpoll.listen():
            try:
                if event.type == VkBotEventType.MESSAGE_NEW and event.obj['from_id'] \
                        in self.admin_list(event.obj['peer_id']):
                    if event.from_chat:
                        if event.object.get('action'):
                            if 'chat_invite' in event.object['action'].get('type'):
                                try:
                                    self.say_rulers(None, event.object['peer_id'])
                                    self.add_user_to_list(event.object['action'].get('member_id'),
                                                          event.object['peer_id'])
                                    self.print_user_list(None, event.object['peer_id'])
                                except Exception as err:
                                    print(err)
                            if 'chat_kick_user' in event.object['action'].get('type'):
                                try:
                                    self.delete_user(f"id{event.object['action']['member_id']}",
                                                     event.object['peer_id'])
                                    self.print_user_list(None, event.object['peer_id'])
                                except Exception as err:
                                    print(err)
                        message = event.obj.text.split(' ')
                        if message[0] in self.user_commands:
                            user_list = self.get_users_id_from_nicknames(message[1:])
                            self.user_commands[message[0]](user_list, event.obj['peer_id'], event.chat_id)
                        if message[0] in self.group_commands:
                            self.group_commands[message[0]](' '.join(message[1:]), event.obj['peer_id'])
            except Exception as err:
                print(err)


if __name__ == "__main__":
    bot = group_bot()
    bot.main()
