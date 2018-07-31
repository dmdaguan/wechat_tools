# -*- coding: utf-8 -*-
import sys, logging
from PyQt5.QtWidgets import (QMainWindow, QFileDialog, QApplication, QMessageBox)
from PyQt5.QtCore import (QThread, pyqtSignal, QObject, pyqtSlot)
from Ui_mainWindow import Ui_wechat_tools

from wechat import *
from configure import *

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    )


class run_wechat(QObject):
    # 进程结束信号
    finished = pyqtSignal()
    # 声明一个登录成功信号
    login_signal = pyqtSignal()
    # 声明一个获取用户名成功信号，参数为登录用户名
    get_username_signal = pyqtSignal(str)
    # 声明一个注销成功信号
    logout_signal = pyqtSignal()
    # 声明一个消息撤回信号
    msg_withdraw_signal = pyqtSignal(str)

    #登录扫码图片
    qr_pic = None

    def __init__(self):
        super().__init__()
        self.single_id = single_wechat_id()

    # 登录成功回调
    @pyqtSlot()
    def on_login_success(self):
        logging.debug('login success')
        # 删除qr图片
        os.remove(self.qr_pic)
        # 发送登录成功信号
        self.login_signal.emit()
        try:
            username = self.single_id.get_self_nickname()
        except Exception as e:
            logging.error(e)
        logging.info(username)
        # 发送成功获取用户名信号
        self.get_username_signal.emit(username)

    # 退出登录回调
    @pyqtSlot()
    def on_logout_success(self):
        logging.debug('logout success')
        # 发送账号退出信号
        self.logout_signal.emit()
        # 发送进程结束信号
        self.finished.emit()
        return

    # 登录微信
    def log_in(self):
        self.home_path = os.path.expandvars('%USERPROFILE%')
        self.work_dir = os.path.join(self.home_path, 'wechat_tools')
        logging.debug('work_dir is ' + self.work_dir)
        self.qr_pic = os.path.join(self.work_dir, 'QR.png')
        logging.debug('qr pic path is ' + self.qr_pic)
        self.status_storage_file = os.path.join(self.work_dir, 'itchat.pkl')
        logging.debug('status storage path is ' + self.status_storage_file)
        if not os.path.isdir(self.work_dir):
            os.makedirs(self.work_dir)
        try:
            self.single_id.login(self.status_storage_file, self.qr_pic, self.on_login_success, self.on_logout_success)
        except Exception as e:
            logging.error(e)
        return

    # 注销登录
    def loggout(self):
        self.single_id.logout()
        # 发送进程结束信号
        self.finished.emit()
        return

    # 微信消息撤回回调
    def msg_withdraw_cb(self, msg):
        logging.info('消息撤回回调')
        logging.info('msg is %s' % msg)
        self.msg_withdraw_signal.emit(msg)
        return

    # 开启微信防撤回
    def enable_message_withdraw(self, file_store_path):
        logging.info('开启消息防撤回')
        self.single_id.enable_message_withdraw(file_store_path, self.msg_withdraw_cb)
        return

    # 关闭微信防撤回
    def disable_message_withdraw(self):
        self.single_id.disable_message_withdraw()
        return

class MainWindow(QMainWindow, Ui_wechat_tools):
    login_button_pressed = False
    msg_withdraw_button_pressed = False
    withdraw_file_store_path = None

    def __init__(self, parent=None):
        super(MainWindow, self).__init__()
        self.setFixedSize(800, 600)

        # 微信登录处理函数
        self.wechat_handle = run_wechat()
        # 多线程
        self.thread = QThread()
        # 连接登录状态信号和槽函数
        self.wechat_handle.login_signal.connect(self.login_ui_set)
        self.wechat_handle.logout_signal.connect(self.logout_ui_set)
        self.wechat_handle.get_username_signal.connect(self.get_uername_success)
        self.wechat_handle.msg_withdraw_signal.connect(self.show_withdraw_msg)
        # 将处理函数与多线程绑定
        self.wechat_handle.moveToThread(self.thread)
        # 连接线程退出信号
        self.wechat_handle.finished.connect(self.thread.quit)
        # 连接线程启动函数
        self.thread.started.connect(self.wechat_handle.log_in)

        self.ui = Ui_wechat_tools()
        self.ui.setupUi(self)

        # 菜单栏
        self.ui.help_contact.triggered.connect(self.setting_cliked)
        self.ui.help_about.triggered.connect(self.help_about_clicked)

        # 按钮
        self.ui.button_login.clicked.connect(self.button_loggin_cliked)
        self.ui.button_withdraw.clicked.connect(self.button_withdraw_message)

        # 按钮全部置灰，登录后才可使用
        self.disable_function_buttons(True)

        # 从配置文件中读取设置
        self.my_config = configure()
        self.read_config_file()

    # 输出log到GUI文本框
    def ui_show_info(self, str):
        self.ui.textBrowser.append(str)

    # 清除文本框显示
    def ui_show_clear(self):
        self.ui.textBrowser.clear()

    # 菜单栏-设置
    def setting_cliked(self):
        print('设置被点击')
        self.file_store_path_get = QFileDialog.getExistingDirectory(self, '选取文件夹', '/home')
        if self.file_store_path_get:
            self.file_store_path = self.file_store_path_get
            # 将设置写入配置文件
            self.my_config.set_withdraw_msg_file_path(self.file_store_path)
            self.ui_show_info('设置文件存储目录成功')
            try:
                # 写入配置文件
                None
            except Exception as e:
                logging.debug(e)
        else:
            self.ui_show_info('未设置文件存储目录')

    # 菜单栏-帮助-关于
    def help_about_clicked(self):
        QMessageBox.about(self, '关于',
                          'version：0.1'
                          '\n'
                          'author: yasin')

    # 扫码登录按钮
    def button_loggin_cliked(self):
        logging.debug('loggin button is cliked!')
        if self.login_button_pressed is False:
            self.login_button_pressed = True
            # 置灰按钮，防止被多次按下
            self.ui.button_login.setDisabled(True)
            # 启动新线程
            self.thread.start()
        else:
            # 注销登录
            self.wechat_handle.loggout()
            self.login_button_pressed = False

    # 消息防撤回按钮
    def button_withdraw_message(self):
        logging.debug('withdraw message button is clicked! ')
        if self.msg_withdraw_button_pressed is False:
            self.msg_withdraw_button_pressed = True
            self.wechat_handle.enable_message_withdraw(self.file_store_path)
            # 改变按钮显示
            self.ui_show_info('消息防撤回开启成功！')
            self.ui.button_withdraw.setText('关闭消息防撤回')
        else:
            self.msg_withdraw_button_pressed = False
            self.wechat_handle.disable_message_withdraw()
            self.ui_show_info('消息防撤回关闭成功！')
            self.ui.button_withdraw.setText('开启消息防撤回')

    # 显示撤回的消息
    def show_withdraw_msg(self, msg):
        self.ui_show_info(msg)

    # 登录成功处理函数
    def login_ui_set(self):
        # 开启其它功能按钮
        self.disable_function_buttons(False)
        # 改变登录按钮显示
        self.ui.button_login.setText('退出登录')
        # 取消按钮置灰，恢复可用
        self.ui.button_login.setDisabled(False)
        # 显示登录成功信息
        self.ui_show_info('登录成功！')
        self.ui_show_info('正在获取用户名及好友信息，请稍后...')

    # 获取用户名成功
    def get_uername_success(self, username):
        # 改变用户名标签
        self.ui.label.setText(username)
        self.ui_show_info('获取用户名及好友信息成功！')

    # 退出登录处理函数
    def logout_ui_set(self):
        # 置灰其他功能按钮
        self.disable_function_buttons(True)
        # 改变登录按钮显示
        self.ui.button_login.setText('扫码登录')
        # 显示退出信息
        self.ui_show_info('账号已退出登录！')
        # 改变用户名标签
        self.ui.label.setText('Not Login')
        # 清除文本框信息
        self.ui_show_clear()

    # 置灰功能按钮
    def disable_function_buttons(self, switch):
        self.ui.button_withdraw.setDisabled(switch)
        self.ui.button_analyze.setDisabled(switch)
        self.ui.button_delete_detection.setDisabled(switch)
        self.ui.button_robot.setDisabled(switch)

    # 读取配置文件
    def read_config_file(self):
        # 读取撤回文件储存路径
        self.withdraw_file_store_path =  self.my_config.get_withdraw_msg_file_path()
        if (self.withdraw_file_store_path != None):
            logging.info(self.withdraw_file_store_path)
            self.ui_show_info('读取配置文件成功！')
        else:
            self.ui_show_info('读取文件储存路径失败')


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
