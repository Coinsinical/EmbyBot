import yaml
import uuid
import pandas as pd
import pymysql
import requests
import yaml
from pyrogram import Client, filters  # 与telegram进行通信所使用的工具包
from sqlalchemy import create_engine
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton


class YamlConfig(object):
    def __init__(self):
        pass

    def read_yaml(self, file, encoding='utf-8'):
        with open(file, encoding=encoding) as f:
            return yaml.load(f.read(), Loader=yaml.FullLoader)

    def write_yaml(self, file, wtdata, encoding='utf-8'):
        with open(file, encoding=encoding, mode='w') as f:
            yaml.dump(wtdata, stream=f, allow_unicode=True)


class HandleSql:
    def __init__(self, config):
        user = config['db_config']['db_user']
        pwd = config['db_config']['db_password']
        host = config['db_config']['db_host']
        port = config['db_config']['db_port']
        database = config['db_config']['db_name']

        self.engine = create_engine(f'mysql+pymysql://%s:%s@%s:%s/%s' % (user, pwd, host, port, database))
        self.conn = pymysql.connect(host=host, user=user, password=pwd, database=database, port=port)
        self.cursor = self.conn.cursor()  # create database connect
        print('数据库已连接,程序成功启动')

    def __del__(self):
        self.cursor.close()
        self.conn.close()
        print("数据库连接已断开")

    def query(self, sql):
        print(sql)
        self.cursor.execute(sql)
        return self.cursor.fetchall()

    def exec(self, sql):
        try:
            print(sql)
            self.cursor.execute(sql)
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            print(str(e))

    def query_user(self, tgid):
        # 查询到结果返回元组，未查询到返回空元组
        return self.query("select * from user where tgid='{}'".format(tgid))

    def check_admin(self, tgid):
        # 查询到结果返回元组，未查询到返回空元组 有数据：tuple of tuple；无数据：() ((11111, 'True', 'None', 'wuiueiw', '1212323', 10002121),)
        return self.query("select * from user where tgid='{}' and admin = 1".format(tgid))

    def select(self, table_name, select_item, condition_dict):
        condition_list = []
        for i in condition_dict:
            condition_list.append("{} = '{}'".format(i, str(condition_dict[i])))
        sql = "select {} from {} where ".format(select_item, table_name) + ' and '.join(condition_list)
        print(sql)
        return self.query(sql)

    def update(self, table_name, data_dict, condition_dict):
        update_list = []
        condition_list = []
        for i in data_dict:
            update_list.append("{}= '{}'".format(str(i), str(data_dict[i])))
        for i in condition_dict:
            condition_list.append("{}= '{}'".format(str(i), str(condition_dict[i])))
        sql = 'UPDATE %s SET ' % table_name + ','.join(update_list) + " WHERE " + ' and '.join(condition_list)
        print(sql)
        self.exec(sql)

    def insert(self, data_dict, table_name):
        key_list = []
        value_list = []
        for i in data_dict:
            key_list.append(i)
            value_list.append(str(data_dict["%s" % i]))
        sql = 'INSERT INTO %s (' % table_name + ','.join(key_list) + \
              ') VALUES ("' + '","'.join(value_list) + '")'
        self.exec(sql)

    def del_user(self, name):
        self.exec("delete from user where emby_name='{}'".format(name))


class HandleEmby:
    pass


class Buttons(object):
    # user buttons
    #
    user_start_buttons = [
        [KeyboardButton("用户注册"), KeyboardButton("用户删除"), KeyboardButton("用户升级"), KeyboardButton("兑换")],
        [KeyboardButton("线路查看"), KeyboardButton("个人信息")]]

    # admin buttons
    admin_start_buttons = [[KeyboardButton("创建邀请码")], [KeyboardButton("用户设置")], [KeyboardButton("注册设置")]]
    admin_user_setting_buttons = [[InlineKeyboardButton("设置管理员", callback_data="/setadmin")],
                                  [InlineKeyboardButton("封禁用户", callback_data="/ban_emby")],
                                  [InlineKeyboardButton("解禁用户", callback_data="/unban_emby")],
                                  [InlineKeyboardButton("删除用户", callback_data="/delete")],
                                  [InlineKeyboardButton("升级用户", callback_data="/upgrade")]]
    admin_register_buttons = [[InlineKeyboardButton("开放注册（时间）", callback_data="/register_all_time")],
                              [InlineKeyboardButton("开放注册（人数）", callback_data="/register_all_user")],
                              [InlineKeyboardButton("开放邀请注册", callback_data="/register_code")],
                              [InlineKeyboardButton("关闭所有注册", callback_data="/close_register")]
                              ]


if __name__ == '__main__':
    ya = YamlConfig()
    config = ya.read_yaml("configs.yaml")  # 读取的配置格式为dict
    print(config)
    sqlworker = HandleSql(config)
    code = f'register-{str(uuid.uuid4())}'
    data_dict = {'code': code, 'tgid': 1111, 'time': 20221106, 'used': 'False'}
    tgid = 1025891105
    r = {'Name':'woaini'}
    sqlworker.update('user', {'emby_name': r['Name']},
                     {'tgid': tgid, 'grade': 0})
