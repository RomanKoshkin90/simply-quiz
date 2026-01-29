Вы можете установить или обновить Yandex Music API с помощью команды:

pip install -U yandex-music
Или вы можете установить из исходного кода с помощью команды:

git clone https://github.com/MarshalX/yandex-music-api
cd yandex-music-api
python setup.py install
Начало работы
Приступив к работе, первым делом необходимо создать экземпляр клиента.

Инициализация синхронного клиента:

from yandex_music import Client

client = Client()
client.init()

# или

client = Client().init()
Инициализация асинхронного клиента:

from yandex_music import ClientAsync

client = ClientAsync()
await client.init()

# или

client = await Client().init()
Вызов init() необходим для получения информации — упрощения будущих запросов.

Работа без авторизации ограничена. Так, например, для загрузки будут доступны только первые 30 секунд аудиофайла. Для понимания всех ограничений зайдите на сайт Яндекс.Музыка в режиме инкогнито и воспользуйтесь сервисом.

Для доступа к личным данным следует авторизоваться. Это осуществляется через токен аккаунта Яндекс.Музыка.

Авторизация:

from yandex_music import Client

client = Client('token').init()
После успешного создания клиента вы вольны в выборе необходимого метода из API. Все они доступны у объекта класса Client. Подробнее в методах клиента в документации.

Пример получения первого трека из плейлиста “Мне нравится” и его загрузки:

from yandex_music import Client

client = Client('token').init()
client.users_likes_tracks()[0].fetch_track().download('example.mp3')
В примере выше клиент получает список треков, которые были отмечены как понравившиеся. API возвращает объект TracksList, в котором содержится список с треками класса TrackShort. Данный класс содержит наиважнейшую информацию о треке и никаких подробностей, поэтому для получения полной версии трека со всей информацией необходимо обратиться к методу fetch_track(). Затем можно скачать трек методом download().

Пример получения треков по ID:

from yandex_music import Client

client = Client().init()
client.tracks(['10994777:1193829', '40133452:5206873', '48966383:6693286', '51385674:7163467'])
В качестве ID трека выступает его уникальный номер и номер альбома. Первым треком из примера является следующий трек:music.yandex.ru/album/1193829/track/10994777

Выполнение запросов с использованием прокси в синхронной версии:

from yandex_music.utils.request import Request
from yandex_music import Client

request = Request(proxy_url='socks5://user:password@host:port')
client = Client(request=request).init()
Примеры Proxy URL:

socks5://user:password@host:port

http://host:port

https://host:port

http://user:password@host

Больше примеров тут: proxies - advanced usage - requests

Выполнение запросов с использованием прокси в асинхронной версии:

from yandex_music.utils.request_async import Request
from yandex_music import ClientAsync

request = Request(proxy_url='http://user:pass@some.proxy.com')
client = await ClientAsync(request=request).init()
Socks прокси не поддерживаются в асинхронной версии.

Про поддерживаемые прокси тут: proxy support - advanced usage - aiohttp

Изучение по примерам
Вот несколько примеров для обзора. Даже если это не ваш подход к обучению, пожалуйста, возьмите и бегло просмотрите их.

Код примеров опубликован в открытом доступе, поэтому вы можете взять его и начать писать вокруг него свой.

Посетите эту страницу, чтобы изучить официальные примеры.

Особенности использования асинхронного клиента
При работе с асинхронной версией библиотеке стоит всегда помнить следующие особенности:

Клиент следует импортировать с названием ClientAsync, а не просто Client.

При использовании методов-сокращений нужно выбирать метод с суффиксом _async.

Пояснение ко второму пункту:

from yandex_music import ClientAsync

client = await ClientAsync('token').init()
liked_short_track = (await client.users_likes_tracks())[0]

# правильно
full_track = await liked_short_track.fetch_track_async()
await full_track.download_async()

# НЕПРАВИЛЬНО
full_track = await liked_short_track.fetch_track()
await full_track.download()
Логирование
Данная библиотека использует модуль logging. Чтобы настроить логирование на стандартный вывод, поместите в начало вашего скрипта следующий код:

import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
Вы также можете использовать логирование в вашем приложении, вызвав logging.getLogger() и установить уровень какой вы хотите:

logger = logging.getLogger()
logger.setLevel(logging.INFO)
Если вы хотите DEBUG логирование:

logger.setLevel(logging.DEBUG)
