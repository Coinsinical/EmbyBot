import yaml
import pandas as pd
import pymysql
import requests
import yaml
from pyrogram import Client, filters  # 与telegram进行通信所使用的工具包
from sqlalchemy import create_engine


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
    def __init__(self,config):
        user = config['db_config']['db_user']
        pwd = config['db_config']['db_password']
        host = config['db_config']['db_host']
        port = config['db_config']['db_port']
        database = config['db_config']['db_name']

        self.engine = create_engine(f'mysql+pymysql://%s:%s@%s:%s/%s' % (user,pwd,host,port,database))
        self.conn = pymysql.connect(host=host, user=user,password=pwd, database=database,port=port)
        self.cursor = self.conn.cursor()  # create database connect
        print('数据库已连接')

    def __del__(self):
        self.cursor.close()
        self.conn.close()

    def query(self, sql):
        self.cursor.execute(sql)
        return self.cursor.fetchall()

    def exec(self, sql):
        try:
            self.cursor.execute(sql)
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            print(str(e))

    def check_user(self, name):
        result = self.query("select * from user where name='{}'".format(name))
        return True if result else False

    def del_user(self, name):
        self.exec("delete from user where name='{}'".format(name))




