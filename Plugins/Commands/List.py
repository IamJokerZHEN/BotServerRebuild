from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
from nonebot.log import logger
from nonebot.params import CommandArg

from Scripts.Config import config
from Scripts.Globals import render_template
from Scripts.Managers import server_manager
from Scripts.Network import get_player_uuid
from Scripts.Utils import Rules, turn_message

logger.debug('加载命令 List 完毕！')
matcher = on_command('list', force_whitespace=True, rule=Rules.command_rule)


@matcher.handle()
async def handle_group(event: GroupMessageEvent, args: Message = CommandArg()):
    server = (args.extract_plain_text().strip()) or None
    flag, response = await get_players(server)
    if flag is False:
        await matcher.finish(response)
    if config.image_mode:
        player_uuids = {}
        for players in response.values():
            for player in players[0]:
                player_uuids[player] = await get_player_uuid(player)
        image = await render_template('List.html', (700, 1000), player_list=response, uuids=player_uuids)
        await matcher.finish(image)
    message = turn_message(list_handler(response))
    await matcher.finish(message)


def list_handler(players: dict):
    if len(players) == 1:
        server_name, players = players.popitem()
        online_count = sum(len(players) for players in players)
        yield F'===== {server_name} 玩家列表 ====='
        yield from format_players(players)
        yield F'当前在线人数共 {online_count} 人'
        return None
    player_count = 0
    if players:
        yield '====== 玩家列表 ======'
        for name, value in players.items():
            if value is None: continue
            player_count += sum(len(players) for players in value)
            yield F' -------- {name} --------'
            yield from format_players(value)
        yield F'当前在线人数共 {player_count} 人'
        return None
    yield '当前没有已连接的服务器！'


def format_players(players: list):
    if config.bot_prefix:
        real_players, fake_players = players
        real_players_str = '\n    '.join(real_players)
        fake_players_str = '\n    '.join(fake_players)
        yield '  ———— 玩家 ————'
        if not real_players_str: real_players_str = '没有玩家在线！'
        yield '    ' + real_players_str
        yield '  ———— 假人 ————'
        if not fake_players_str: fake_players_str = '没有假人在线！'
        yield '    ' + fake_players_str + '\n'
        return None
    if players := players[0]:
        yield '    ' + '\n    '.join(players) + '\n'
        return None
    yield '  没有玩家在线！\n'


def classify_players(players: list | None):
    if players is None:
        players = []

    # 统一成字符串
    if isinstance(players, (list, tuple)):
        players = ','.join(players)      # 列表也先拼成串，方便后面统一处理

    # 按逗号/换行/分号都可以切，去掉空元素
    import re
    players = [p.strip() for p in re.split(r'[,\n;]|\r\n', players) if p.strip()]

    # 后面你原来的逻辑
    if not config.bot_prefix:
        return players, []
    real, fake = [], []
    for p in players:
        (fake if p.upper().startswith(config.bot_prefix) else real).append(p)
    return real, fake
async def get_players(server_flag: str = None):
    if server_flag is None:
        players = {}
        for name, server in server_manager.servers.items():
            if not server.status:
                continue
            # ③ 在这里加：拿到 None 就换成空列表
            raw_list = await server.send_player_list() or []
            players[name] = classify_players(raw_list)
        return True, players

    # 单服务器分支同理
    server = server_manager.get_server(server_flag)
    if not server:
        return False, f'没有找到已连接的 [{server_flag}] 服务器！请检查编号或名称是否输入正确。'
    raw_list = ((await server.send_player_list()) or {}).get('data') or []   # 同样处理
    return True, {server.name: classify_players(raw_list)}
