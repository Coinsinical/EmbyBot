import json
import random
import string
import time
import uuid
from datetime import datetime, timedelta

import pandas as pd
import pymysql
import requests
import yaml
from pyrogram.types import (ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton)

import tools
import pyrogram  # 与telegram进行通信所使用的工具包
from sqlalchemy import create_engine

chat_step = {}
# 读取配置文件
ya = tools.YamlConfig()
config = (ya.read_yaml('configs.yaml'))
db_name = config['db_config']['db_name']
embyapi = config['emby_config']['embyapi']
embyurl = config['emby_config']['embyurl']

# 创建数据库及机器人连接
sqlworker = tools.HandleSql(config)
app = pyrogram.Client("my_bot", api_id=config['bot_config']['api_id'], api_hash=config['bot_config']['api_hash'],
                      bot_token=config['bot_config']['bot_token'])  # create tg bot


# 加载时间
def LocalTime(time=''):
    n_LastLogin = time[0:19]
    UTC_FORMAT = "%Y-%m-%dT%H:%M:%S"
    utcTime_LastLogin = datetime.strptime(n_LastLogin, UTC_FORMAT)
    localtime_LastLogin = utcTime_LastLogin + timedelta(hours=8)
    return localtime_LastLogin  # change emby time to Asia/Shanghai time


def IsReply(message=''):
    try:
        tgid = message.reply_to_message.from_user.id
    except AttributeError:
        return False
    return tgid


async def CreateCode(tgid=0):
    code = f'register-{str(uuid.uuid4())}'
    data_dict = {'code': code, 'tgid': tgid, 'time': int(time.time()), 'used': 'False'}
    sqlworker.insert(data_dict, "invite_code")
    return code


async def set_admin(tgid=0):
    sqlworker.exec("UPDATE user SET admin = 1 WHERE tgid = {}".format(tgid))


async def invite(tgid=0, message=''):
    if canrig(tgid=tgid) == 'B' or hadname(tgid=tgid) == 'B':
        return 'D'  # have an account or have the chance to register

    message = message.split(' ')
    code = message[-1]  # get the code
    print("select * from invite_code where code ='{}'".format(code))
    code_data = sqlworker.query("select * from invite_code where code ='{}'".format(code))
    if not code_data:
        return 'A'

    if code_data[0][3] == 'True':
        return 'B'  # the code has been used
    else:
        code_used = "UPDATE invite_code SET used = 'True' WHERE code ='{}'".format(code)
        sqlworker.exec(code_used)  # set the code has been used

    # if the tgid is not in the database.add it
    if not sqlworker.query("SELECT * FROM user WHERE tgid = '{}' and grade = 0".format(tgid)):
        data_dict = {'tgid': tgid, 'admin': 0, 'canrig': 'True'}
        sqlworker.insert(data_dict, 'user')
        return 'C'

    # if the tgid is in the database,open the right to it
    setcanrig = "UPDATE user SET canrig ='True' WHERE `tgid`='{tgid}';".format(tgid=tgid)
    sqlworker.exec(setcanrig)  # update the status that can register
    return 'C'  # done


# check if the user can register
def canrig(tgid=0):
    '''
    :param tgid: user tgid
    :return: 'A' means the user is not in the database
             'B' means the user can register
             ‘C' means the user can not register
    '''

    simple_acc = sqlworker.query(
        "SELECT * FROM user WHERE tgid = '{}' and grade = 0".format(tgid))  # get the num of the acc
    if not simple_acc:  # if result tuple is empty,the length may be 0,1,2
        return 'A'

    if simple_acc[0][5] == 'True':
        return 'B'  # can register
    else:
        return 'C'  # cannot register


def hadname(tgid=0):
    user_info = sqlworker.query(
        "SELECT * FROM user WHERE tgid = '{}' and grade = 0".format(tgid))
    if not user_info:
        return 'A'

    if user_info[0][3] != 'None':
        return 'B'  # have an account
    else:
        return 'C'  # does not have an account


# TODO put the time into the database
async def register_all_time(tgid=0, message=''):  # public register
    if sqlworker.check_admin(tgid):
        message = message.split(' ')
        message = message[-1]
        write_conofig(config='register_public', parms='True')
        write_conofig(config='register_public_time', parms=int(time.time()) + (int(message) * 60))
        write_conofig(config='register_method', parms='Time')
        return int(time.time()) + (int(message) * 60)
    else:
        return 'A'  # not an admin


# TODO put the user into the database
async def register_all_user(tgid=0, message=''):
    if sqlworker.check_admin(tgid):
        message = message.split(' ')
        message = message[-1]
        write_conofig(config='register_public', parms='True')
        write_conofig(config='register_public_user', parms=int(message))
        write_conofig(config='register_method', parms='User')
        return int(message)
    else:
        return 'A'  # not an admin


def userinfo(tgid='0'):
    usr_data = []
    user_info_tuple = sqlworker.query_user(tgid)
    if not user_info_tuple:
        return 'NotInTheDatabase'

    for user_info in user_info_tuple:
        bantime = user_info[6]
        emby_name = user_info[3]
        emby_id = user_info[4]
        canrig = user_info[5]
        grade = user_info[7]
        if grade == 0:
            grade = "普通用户"
        else:
            grade = "高级用户"

        if bantime == 0:
            bantime = 'None'
        else:
            expired = time.localtime(bantime)
            expired = time.strftime("%Y/%m/%d %H:%M:%S", expired)  # change the time format
            bantime = expired
        if emby_name != 'None':
            r = requests.get(
                f"{config['emby_config']['embyurl']}/emby/users/{emby_id}?api_key={config['emby_config']['embyapi']}").text
            r = json.loads(r)
            try:
                lastacttime = r['LastActivityDate']
                createdtime = r['DateCreated']
                lastacttime = LocalTime(time=lastacttime)
                createdtime = LocalTime(time=createdtime)
            except KeyError:
                lastacttime = 'None'
                createdtime = 'None'
            usr_data.append(['HaveAnEmby', emby_name, emby_id, lastacttime, createdtime, bantime, grade])
        else:
            usr_data.append(['NotHaveAnEmby', canrig])
    return usr_data


def prichat(message=''):
    if str(message.chat.type) == 'ChatType.PRIVATE':
        return True
    else:
        return False


async def BanEmby(tgid=0, message='', replyid=0):
    if sqlworker.check_admin(tgid=tgid):
        if hadname(tgid=replyid) == 'B':
            user_info = sqlworker.query_user(replyid)
            if not user_info:
                return 'NotInTheDatabase'

            embyapi = config['emby_config']['embyapi']
            embyurl = config['emby_config']['embyurl']
            emby_name = user_info[0][2]
            emby_id = user_info[0][3]
            db_name = 'user'
            params = (('api_key', embyapi),
                      )
            headers = {
                'accept': 'application/json',
                'Content-Type': 'application/json',
            }
            data = '{"IsAdministrator":false,"IsHidden":true,"IsHiddenRemotely":true,"IsDisabled":true,"EnableRemoteControlOfOtherUsers":false,"EnableSharedDeviceControl":false,"EnableRemoteAccess":true,"EnableLiveTvManagement":false,"EnableLiveTvAccess":true,"EnableMediaPlayback":true,"EnableAudioPlaybackTranscoding":false,"EnableVideoPlaybackTranscoding":false,"EnablePlaybackRemuxing":false,"EnableContentDeletion":false,"EnableContentDownloading":false,"EnableSubtitleDownloading":false,"EnableSubtitleManagement":false,"EnableSyncTranscoding":false,"EnableMediaConversion":false,"EnableAllDevices":true,"SimultaneousStreamLimit":3}'
            requests.post(embyurl + '/emby/Users/' + emby_id + '/Policy',
                          headers=headers,
                          params=params, data=data)  # update policy
            setbantime = f"UPDATE `user` SET `bantime`={int(time.time())} WHERE  `tgid`='{tgid}';"
            sqlworker.exec(setbantime)  # update the status that cannot register
            return 'A', emby_name  # Ban the user's emby account
        else:
            if canrig(tgid=replyid):
                setcanrig = f"UPDATE `user` SET `canrig`='F' WHERE  `tgid`='{replyid}';"
                sqlworker.exec(setcanrig)  # update the status that cannot register
                return 'C', 'CannotReg'  # set cannot register
            else:
                return 'D', 'DoNothing'  # do nothing
    else:
        return 'B', 'NotAnAdmin'  # Not an admin


async def UnbanEmby(tgid=0, message='', replyid=0):
    if sqlworker.check_admin(tgid=tgid):
        if hadname(tgid=replyid) == 'B':
            user_info = sqlworker.query_user(replyid)
            if not user_info:
                return 'NotInTheDatabase'

            for user_data in user_info:
                embyapi = config['emby_config']['embyapi']
                embyurl = config['emby_config']['embyurl']
                emby_name = user_data[3]
                emby_id = user_data[4]

                params = (('api_key', embyapi),
                          )
                headers = {
                    'accept': 'application/json',
                    'Content-Type': 'application/json',
                }
                data = '{"IsAdministrator":false,"IsHidden":true,"IsHiddenRemotely":true,"IsDisabled":false,' \
                       '"EnableRemoteControlOfOtherUsers":false,"EnableSharedDeviceControl":false,"EnableRemoteAccess":true,' \
                       '"EnableLiveTvManagement":false,"EnableLiveTvAccess":true,"EnableMediaPlayback":true,' \
                       '"EnableAudioPlaybackTranscoding":false,"EnableVideoPlaybackTranscoding":false,' \
                       '"EnablePlaybackRemuxing":false,"EnableContentDeletion":false,"EnableContentDownloading":false,' \
                       '"EnableSubtitleDownloading":false,"EnableSubtitleManagement":false,"EnableSyncTranscoding":false,' \
                       '"EnableMediaConversion":false,"EnableAllDevices":true,"SimultaneousStreamLimit":3}'
                requests.post(embyurl + '/emby/Users/' + emby_id + '/Policy',
                              headers=headers,
                              params=params, data=data)  # update policy
            setbantime = f"UPDATE `user` SET `bantime`={0} WHERE  `tgid`='{replyid}';"
            sqlworker.exec(setbantime)  # update the status that cannot register
            return 'A', emby_name  # Unban the user's emby account
        else:
            return 'C', 'DoNothing'  # do nothing
    else:
        return 'B', 'NotAnAdmin'  # Not an admin


async def upgrade(embyname):
    emby_id = sqlworker.select('user', 'emby_id', {'emby_name': embyname})[0][0]
    print(id)
    params = (('api_key', embyapi),
              )
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
    }
    data1 = '{"IsAdministrator":false,"IsHidden":true,"IsHiddenRemotely":true,"IsDisabled":false,' \
            '"EnableRemoteControlOfOtherUsers":false,"EnableSharedDeviceControl":false,"EnableRemoteAccess":true,' \
            '"EnableLiveTvManagement":false,"EnableLiveTvAccess":true,"EnableMediaPlayback":true,' \
            '"EnableAudioPlaybackTranscoding":false,"EnableVideoPlaybackTranscoding":false,' \
            '"EnablePlaybackRemuxing":false,"EnableContentDeletion":false,"EnableContentDownloading":true,' \
            '"EnableSubtitleDownloading":true,"EnableSubtitleManagement":false,"EnableSyncTranscoding":false,' \
            '"EnableMediaConversion":false,"EnableAllDevices":true,"SimultaneousStreamLimit":3}'
    requests.post(embyurl + '/emby/Users/' + emby_id + '/Policy', headers=headers,
                  params=params, data=data1)  # update policy
    sqlworker.update('user', {'grade': 1}, {'emby_name': embyname})


async def delete(tgid, message):
    name = message.split(' ')[-1]
    if name == '' or name == ' ':
        return 'B'  # do not input a name

    user_data = sqlworker.select('user', '*', {'tgid': tgid, 'emby_name': name})
    print(user_data)
    if not user_data:
        return 'A'

    params = (('api_key', embyapi),
              )
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
    }
    emby_id = user_data[0][4]
    r = requests.post(url=embyurl + '/emby/Users/' + emby_id + '/Delete', headers=headers,
                  params=params).text  # update policy
    sqlworker.del_user(name=name)
    return name


async def create(tgid=0, message=''):  # register with invite code
    message = message.split(' ')
    name = message[-1]
    if name == '' or name == ' ':
        return 'B'  # do not input a name
    data = '{"Name":"' + name + '","HasPassword":true}'
    params = (('api_key', embyapi),
              )
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
    }
    r = requests.post(url=embyurl + '/emby/Users/New', headers=headers, params=params, data=data).text
    try:
        r = json.loads(r)  # create a new user
    except json.decoder.JSONDecodeError:
        if r.find('already exists.'):
            return 'D'  # already exists
    data1 = '{"IsAdministrator":false,"IsHidden":true,"IsHiddenRemotely":true,"IsDisabled":false,' \
            '"EnableRemoteControlOfOtherUsers":false,"EnableSharedDeviceControl":false,"EnableRemoteAccess":true,' \
            '"EnableLiveTvManagement":false,"EnableLiveTvAccess":true,"EnableMediaPlayback":true,' \
            '"EnableAudioPlaybackTranscoding":false,"EnableVideoPlaybackTranscoding":false,' \
            '"EnablePlaybackRemuxing":false,"EnableContentDeletion":false,"EnableContentDownloading":false,' \
            '"EnableSubtitleDownloading":false,"EnableSubtitleManagement":false,"EnableSyncTranscoding":false,' \
            '"EnableMediaConversion":false,"EnableAllDevices":true,"SimultaneousStreamLimit":3}'

    requests.post(embyurl + '/emby/Users/' + r['Id'] + '/Policy', headers=headers,
                  params=params, data=data1)  # update policy
    NewPw = ''.join(random.sample(string.ascii_letters + string.digits, 8))
    data = '{"CurrentPw":"" , "NewPw":"' + NewPw + '","ResetPassword" : false}'
    requests.post(f"{embyurl}/emby/users/{r['Id']}/Password?api_key={embyapi}", headers=headers, data=data)

    if not sqlworker.query_user(tgid):
        data_dict = {'tgid': tgid, 'admin': 0, 'emby_name': str(r['Name']), 'emby_id': str(r['Id']), 'canrig': 'False'}
        sqlworker.insert(data_dict, 'user')  # add the user info
        return r['Name'], NewPw

    # 如果数据库已有用户
    sqlworker.update('user', {'emby_name': r['Name'], 'canrig': 'False', 'emby_id': r['Id']},
                     {'tgid': tgid, 'grade': 0})
    return r['Name'], NewPw


async def create_time(tgid=0, message=''):
    register_public_time = sqlworker.select('config', 'register_public_time', {"id": 1})[0][0]
    if int(time.time()) < register_public_time:
        message = message.split(' ')
        name = message[-1]
        if name == '' or name == ' ':
            return 'B'  # do not input a name
        data = '{"Name":"' + name + '","HasPassword":true}'
        params = (('api_key', embyapi),
                  )
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
        }
        r = requests.post(url=embyurl + '/emby/Users/New', headers=headers,
                          params=params, data=data).text
        try:
            r = json.loads(r)  # create a new user
        except json.decoder.JSONDecodeError:
            if r.find('already exists.'):
                return 'D'  # already exists
        data1 = '{"IsAdministrator":false,"IsHidden":true,"IsHiddenRemotely":true,"IsDisabled":false,"EnableRemoteControlOfOtherUsers":false,"EnableSharedDeviceControl":false,"EnableRemoteAccess":true,"EnableLiveTvManagement":false,"EnableLiveTvAccess":true,"EnableMediaPlayback":true,"EnableAudioPlaybackTranscoding":false,"EnableVideoPlaybackTranscoding":false,"EnablePlaybackRemuxing":false,"EnableContentDeletion":false,"EnableContentDownloading":false,"EnableSubtitleDownloading":false,"EnableSubtitleManagement":false,"EnableSyncTranscoding":false,"EnableMediaConversion":false,"EnableAllDevices":true,"SimultaneousStreamLimit":3}'
        requests.post(embyurl + '/emby/Users/' + r['Id'] + '/Policy',
                      headers=headers,
                      params=params, data=data1)  # update policy
        NewPw = ''.join(random.sample(string.ascii_letters + string.digits, 8))
        data = '{"CurrentPw":"" , "NewPw":"' + NewPw + '","ResetPassword" : false}'
        requests.post(f"{embyurl}/emby/users/{r['Id']}/Password?api_key={embyapi}",
                      headers=headers, data=data)

        if not sqlworker.query("SELECT * FROM user WHERE tgid = '{}' and grade = 0".format(tgid)):
            data_dict = {'tgid': tgid, 'admin': 0, 'emby_name': str(r['Name']), 'emby_id': str(r['Id']),
                         'canrig': 'False'}
            sqlworker.insert(data_dict, 'user')
            return r['Name'], NewPw

        sqlworker.update('user', {'emby_name': r['Name'], 'canrig': 'False', 'emby_id': r['Id']},
                         {'tgid': tgid, 'grade': 0})
        return r['Name'], NewPw
    else:
        register_method = 'None'
        write_conofig(config='register_method', parms='None')
        write_conofig(config='register_public_time', parms=0)
        return 'C'


async def create_user(tgid=0, message=''):
    register_public_user = sqlworker.select('config', 'register_public_user', {"id": 1})[0][0]  # 加载可创建
    if register_public_user > 0:
        message = message.split(' ')
        name = message[-1]
        if name == '' or name == ' ':
            return 'B'  # do not input a name
        data = '{"Name":"' + name + '","HasPassword":true}'
        params = (('api_key', embyapi),
                  )
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
        }
        r = requests.post(url=embyurl + '/emby/Users/New', headers=headers,
                          params=params, data=data).text
        try:
            r = json.loads(r)  # create a new user
        except json.decoder.JSONDecodeError:
            print(r)
            if r.find('already exists.'):
                return 'D'  # already exists
        data1 = '{"IsAdministrator":false,"IsHidden":true,"IsHiddenRemotely":true,"IsDisabled":false,"EnableRemoteControlOfOtherUsers":false,"EnableSharedDeviceControl":false,"EnableRemoteAccess":true,"EnableLiveTvManagement":false,"EnableLiveTvAccess":true,"EnableMediaPlayback":true,"EnableAudioPlaybackTranscoding":false,"EnableVideoPlaybackTranscoding":false,"EnablePlaybackRemuxing":false,"EnableContentDeletion":false,"EnableContentDownloading":false,"EnableSubtitleDownloading":false,"EnableSubtitleManagement":false,"EnableSyncTranscoding":false,"EnableMediaConversion":false,"EnableAllDevices":true,"SimultaneousStreamLimit":3}'
        requests.post(embyurl + '/emby/Users/' + r['Id'] + '/Policy',
                      headers=headers,
                      params=params, data=data1)  # update policy
        NewPw = ''.join(random.sample(string.ascii_letters + string.digits, 8))
        data = '{"CurrentPw":"" , "NewPw":"' + NewPw + '","ResetPassword" : false}'
        requests.post(f"{embyurl}/emby/users/{r['Id']}/Password?api_key={embyapi}",
                      headers=headers, data=data)
        if not sqlworker.query("SELECT * FROM user WHERE tgid = '{}' and grade = 0".format(tgid)):
            data_dict = {'tgid': tgid, 'admin': '0', 'emby_name': str(r['Name']), 'emby_id': str(r['Id']),
                         'canrig': 'False'}
            sqlworker.insert(data_dict, 'user')  # add the user info
            write_conofig(config='register_public_user', parms=register_public_user - 1)
            return r['Name'], NewPw
        sqlworker.update('user', {'emby_name': r['Name'], 'canrig': 'False', 'emby_id': r['Id']},
                         {'tgid': tgid, 'grade': 0})
        write_conofig(config='register_public_user', parms=register_public_user - 1)
        return r['Name'], NewPw
    else:
        write_conofig(config='register_method', parms='None')
        write_conofig(config='register_public_user', parms=0)
        return 'C'


def write_conofig(config='', parms=''):
    sqlsen = f"UPDATE `{db_name}`.`config` SET `{config}`='{parms}' WHERE  `id`='1';"
    sqlworker.exec(sqlsen)
    return 'OK'


@app.on_callback_query()
async def answer(client, callback_query):
    global chat_step
    tgid = callback_query.from_user.id
    chat_step[tgid] = callback_query.data
    message = callback_query.message
    if callback_query.data == '/setadmin':
        content = "请输入需要设置的管理员telegram ID"
    if callback_query.data == '/register_all_time':
        content = "请输入开放注册的时间（分）"
    if callback_query.data == '/register_all_user':
        content = "请输入开放注册的人数"
    if callback_query.data == '/register_code':
        write_conofig("register_public", 'True')
        write_conofig("register_method", 'None')
        content = "已开启仅邀请注册"
        chat_step[tgid] = ''
    if callback_query.data == '/close_register':
        write_conofig("register_public", 'False')
        content = "注册已关闭"
        chat_step[tgid] = ''
    if callback_query.data == '/ban_emby':
        content = '请输入需要禁用的用户telegram ID'
    if callback_query.data == '/unban_emby':
        content = '请输入需要禁用的用户telegram ID'
    await message.reply(content)


@app.on_message(pyrogram.filters.text)
async def my_handler(client, message):
    global chat_step
    buttons = tools.Buttons
    bot_name = config['bot_config']['bot_name']
    ban_channel_id = config['tg_config']['ban_channel_id']
    line = config['emby_config']['line']

    tgid = message.from_user.id
    try:
        text = chat_step[tgid] + ' ' + str(message.text)
    except KeyError:
        text = str(message.text)

    print(text)
    if str(text) == '/start' or text == f'/start{bot_name}':
        # one list represents one line,you can put serval button in one list and show them in one line
        if sqlworker.check_admin(tgid):
            markup = ReplyKeyboardMarkup(buttons.admin_start_buttons, resize_keyboard=True)
        else:
            markup = ReplyKeyboardMarkup(buttons.user_start_buttons, resize_keyboard=True)
        await message.reply(
            '请选择你需要的操作', reply_markup=markup)

    elif str(text).find('用户注册') != -1:
        if prichat(message=message):
            register_public = sqlworker.select('config', 'register_public', {"id": 1})[0][0]
            if register_public == 'True':
                register_method = sqlworker.select('config', 'register_method', {"id": 1})[0][0]
                if register_method == 'None':
                    if hadname(tgid=tgid) == 'B':
                        re = 'A'  # already have an account
                    elif canrig(tgid=tgid) != 'B':
                        re = 'C'  # cannot register
                    else:
                        re = 'B'

                elif register_method == 'User':
                    register_public_user = sqlworker.select('config', 'register_public_user', {"id": 1})[0][0]  # 加载可创建
                    if register_public_user > 0:
                        if hadname(tgid=tgid) == 'B':
                            re = 'A'  # already have an account
                        else:
                            re = 'B'
                    else:
                        re = 'D'
                elif register_method == 'Time':
                    register_public_time = sqlworker.select('config', 'register_public_time', {"id": 1})[0][0]
                    if int(time.time()) < register_public_time:
                        if hadname(tgid=tgid) == 'B':
                            re = 'A'  # already have an account
                        else:
                            re = 'B'
                    else:
                        re = 'D'

                if re == 'A':
                    await message.reply('您已经注册过emby账号，请勿重复注册')
                elif re == 'B':
                    await  message.reply("请输入你的Emby用户名")
                    chat_step[tgid] = '/create'
                elif re == 'C':
                    await message.reply('您还未获得注册资格，请点击下方按钮进行兑换')
                else:
                    await message.reply("注册已经结束，请期待下次注册")
            else:
                await message.reply('目前尚未开放注册，请关注开注通知')
        else:
            await message.reply('请勿在群组使用该命令')

    elif str(text).find("用户升级") != -1:
        await message.reply("升级功能尚未开放")

    elif str(text).find("个人信息") != -1 or text == f'/info{bot_name}':
        replyid = IsReply(message=message)
        if replyid != False:
            re = userinfo(tgid=replyid)
            if sqlworker.check_admin(tgid=tgid):
                if re == 'NotInTheDatabase':
                    await message.reply('用户未入库，无信息')
                elif re[0][0] == 'HaveAnEmby':
                    await message.reply('用户信息已PM')
                    await app.send_message(chat_id=tgid,
                                           text=f'用户<a href="tg://user?id={replyid}">{replyid}</a>的信息\nEmby Name: {re[1]}\n Emby ID: {re[2]}\n上次活动时间{re[3]}\n账号创建时间{re[4]}\n被ban时间{re[5]}')
                elif re[0][0] == 'NotHaveAnEmby':
                    await message.reply(f'此用户没有emby账号，可注册：{re[1]}')
            else:
                await message.reply('非管理员请勿随意查看他人信息')
        else:
            re = userinfo(tgid=tgid)
            if re == 'NotInTheDatabase':
                await message.reply('用户未入库，无信息')
            elif re[0][0] == 'HaveAnEmby':
                text = []
                for reply in re:
                    text.append(f'用户<a href="tg://user?id={tgid}">{tgid}</a>的信息\nEmby等级：{reply[6]}\n'
                                f'Emby Name: {reply[1]}\n Emby ID: {reply[2]}\n上次活动时间：{reply[3]}\n账号创建时间：{reply[4]}\n被ban时间：{reply[5]}')
                text = '\n\n'.join(text)
                await message.reply('用户信息已私发，请查看')
                await app.send_message(chat_id=tgid, text=text)
            elif re[0][0] == 'NotHaveAnEmby':
                await message.reply(f'此用户没有emby账号，可注册：{re[0][1]}')


    elif text.find('线路查看') != -1:
        if prichat(message=message):
            if hadname(tgid=tgid) == 'B':
                await message.reply(line)
            else:
                await message.reply('无Emby账号无法查看线路')
        else:
            await message.reply('请勿在群组中使用此命令')

    elif str(text).find('兑换') != -1:
        if prichat(message=message):
            await message.reply('请输入兑换码')
            chat_step[tgid] = '/input_code'
        else:
            await message.reply('请勿在群组使用该命令')

    elif str(text).find('用户删除') != -1:
        await message.reply("请输入需要删除的emby用户名")
        chat_step[tgid] = '/delete'

    # 管理员操作
    elif str(text).find("用户设置") != -1:
        if sqlworker.check_admin(tgid=tgid):
            markup = InlineKeyboardMarkup(buttons.admin_user_setting_buttons)
            await message.reply('请选择你需要的操作', reply_markup=markup)
        else:
            await message.reply('不是管理员请勿使用管理员命令')

    elif str(text).find("创建邀请码") != -1:
        if sqlworker.check_admin(tgid=tgid):
            re = await CreateCode(tgid=tgid)
            if not IsReply(message=message):
                await message.reply(f'生成成功，邀请码<code>{re}</code>')
        else:
            await message.reply('不是管理员请勿使用管理员命令')

    elif str(text).find("注册设置") != -1:
        if sqlworker.check_admin(tgid=tgid):
            markup = InlineKeyboardMarkup(buttons.admin_register_buttons)
            await message.reply('请选择你需要的操作', reply_markup=markup)
        else:
            await message.reply('不是管理员请勿使用管理员命令')

    elif str(text).find('/delete') != -1:
        r = await delete(tgid,str(message.text))
        if r == 'B':
            content = "未输入用户名，请重新输入"
        elif r == 'A':
            content = "该用户名未与你的telegram账号绑定，请确认后重新输入"
        else:
            content = '用户' + r + '已被删除'
            chat_step[tgid] = ''
        await message.reply(content)

    elif str(text).find("/setadmin") != -1:
        usr_tgid = text.split(" ")[1]
        if not sqlworker.check_admin(usr_tgid):
            await set_admin(usr_tgid)
            if sqlworker.check_admin(usr_tgid):
                content = "管理员已设置完毕"
                chat_step[tgid] = ''
            else:
                content = "管理员设置失败，请重新输入管理员ID"
        else:
            content = "该用户已经是管理员，无需设置"
            chat_step[tgid] = ''
        await message.reply(content)

    elif str(text).find('/ban_emby') != -1:
        if IsReply(message=message):
            replyid = IsReply(message=message)
        else:
            replyid = message.text.split(' ')[-1]

        re = await BanEmby(tgid=tgid, message=message, replyid=replyid)
        if re[0] == 'A':
            await message.reply(f'用户<a href="tg://user?id={replyid}">{replyid}</a>的Emby账号{re[1]}已被封禁')
            await app.send_message(chat_id=ban_channel_id,
                                   text=f'#Ban\n用户：<a href="tg://user?id={replyid}">{replyid}</a>\nEmby账号：{re[1]}\n原因：管理员封禁')
        elif re[0] == 'B':
            await message.reply('请勿随意使用管理员命令')
        elif re[0] == 'C':
            await message.reply(f'用户<a href="tg://user?id={replyid}">{replyid}</a>没有Emby账号，但是已经取消了他的注册资格')
        elif re[0] == 'D':
            await message.reply(f'用户<a href="tg://user?id={replyid}">{replyid}</a>没有Emby账号，也没有注册资格')

    elif str(text).find('/unban_emby') != -1:
        if IsReply(message=message):
            replyid = IsReply(message=message)
        else:
            replyid = message.text.split(' ')[-1]

        re = await UnbanEmby(tgid=tgid, message=message, replyid=replyid)
        if re[0] == 'A':
            await message.reply(f'用户<a href="tg://user?id={replyid}">{replyid}</a>的Emby账号{re[1]}已解除封禁')
            await app.send_message(chat_id=ban_channel_id,
                                   text=f'#Unban\n用户：<a href="tg://user?id={replyid}">{replyid}</a>\nEmby账号：{re[1]}\n原因：管理员解封')
        elif re[0] == 'B':
            await message.reply('请勿随意使用管理员命令')
        elif re[0] == 'C':
            await message.reply(f'用户<a href="tg://user?id={replyid}">{replyid}</a>没有Emby账号，也没有注册资格')

    # 开放注册

    elif str(text).find('/register_all_time') != -1:
        re = await register_all_time(tgid=tgid, message=text)
        if re == 'A':
            await message.reply('您不是管理员，请勿随意使用管理命令')
        else:
            expired = time.localtime(re)
            expired = time.strftime("%Y/%m/%d %H:%M:%S", expired)
            chat_step[tgid] = ''
            await message.reply(f"注册已开放，将在{expired}关闭注册")

    elif str(text).find('/register_all_user') != -1:
        re = await register_all_user(tgid=tgid, message=text)
        if re == 'A':
            await message.reply('您不是管理员，请勿随意使用管理命令')
        else:
            chat_step[tgid] = ''
            await message.reply(f"注册已开放，本次共有{re}个名额")

    elif str(text).find('/input_code') != -1:
        if prichat(message=message):
            re = await invite(tgid=tgid, message=str(message.text))
            if re == 'A':
                await message.reply('没有找到这个邀请码')
            if re == 'B':
                await message.reply('邀请码已被使用')
            if re == 'C':
                await message.reply('恭喜您获得了注册资格，邀请码已失效,请输入用户名')
                chat_step[tgid] = '/create'
            if re == 'D':
                await message.reply('您已有账号或已经获得注册资格，请不要重复使用邀请码')
                chat_step[tgid] = ''
        else:
            await message.reply('请勿在群组使用该命令')


    elif str(text).find('/create') != -1:
        if prichat(message=message):
            register_method = sqlworker.select('config', 'register_method', {"id": 1})[0][0]
            if register_method == 'None':
                re = await create(tgid=tgid, message=str(message.text))
            elif register_method == 'User':
                re = await create_user(tgid=tgid, message=text)
            elif register_method == 'Time':
                re = await create_time(tgid=tgid, message=text)
            if re == 'A':
                await message.reply('您已经注册过emby账号，请勿重复注册')
            elif re == 'C':
                await message.reply('您还未获得注册资格，请输入邀请码')
                chat_step[tgid] = '/input_code'
            elif re == 'B':
                await message.reply('请再次输入用户名，用户名不要包含空格')
            elif re == 'D':
                await message.reply('该用户名已被使用')
            else:
                await message.reply(f'创建成功，账号<code>{re[0]}</code>，初始密码为<code>{re[1]}</code>，密码不进行保存，请尽快登陆修改密码')
                chat_step[tgid] = ''
        else:
            await message.reply('请勿在群组使用该命令')

app.run()
