# -*- coding: utf-8 -*-
import re
import os
import sys
import public_features as PF
from extract_text import extract_text
import threading
import copy
import argparse



# 目录页URL
html_url = 'http://www.piaotian.net/html/5/5924/'

ide_debug = '-s http://bbs.northernbbs.com/thread-670859-1-1.html'

Error_url = ['']
Unable_write = ['']


def extract_url(ori_url, retry=0):
    """
    提取目录页的有效URL，抓取网站title
    :param ori_url: 目录页URL
    :return:        提取的章节URL 列表
    """
    PF.loggings.debug('Open original url %s' % ori_url)
    try:
        soup_text, protocol, ori_domain, rest, code = PF.get_url_to_bs(ori_url, re_count=retry)
    except BaseException as err:
        PF.loggings.error(str(err))
        PF.loggings.debug('Script Exit')
        sys.exit(-1)
    else:
        PF.loggings.debug('Open original url complete！')
        if 'qidian.com' in ori_domain:
            import qidian_config
            PF.loggings.info('Use "qidian" Configure')
            qidian_config.main(ori_url)
            sys.exit(0)

        PF.loggings.debug('Start the analysis original html doc...')
        get_page_links = PF.get_page_links(soup_text, rest, protocol)
        all_page_links = get_page_links.get_href()

        '''初始化中文数字转 int'''
        c2d = PF.chinese_to_digits()

        def match_chinese(s):
            try:
                re_s = re.match('[第卷]?\s*([零一二三四五六七八九十百千万亿]+)', s).group(1)
            except AttributeError:
                re_s = '零'
            return re_s

        PF.loggings.debug('Try to get the Chinese value for each title')
        chinese_str = map(match_chinese, [x[-1] for x in all_page_links])
        PF.loggings.debug('make variable chinese_str duplicate')
        test_number = copy.deepcopy(chinese_str)

        PF.loggings.debug('Began to Analyze the order of the article list...')
        xx = list(map(c2d.run, list(test_number)))
        test_number_str = ''.join([str(x) for x in xx])

        count = 0
        enabel_digtes = True
        if re.match('0*?123456789', test_number_str):
            enabel_digtes = False
            PF.loggings.debug('The article list is sorted correctly :)')
        else:
            PF.loggings.debug('Article list sort exception :( Start the collating sequence')

        for page_group in chinese_str:
            if enabel_digtes:
                digtes = c2d.run(page_group)
                all_page_links[count].append(digtes)
            else:
                '''目录顺不正常，无需排序 只添加序号'''
                all_page_links[count].append(count)
            count += 1
        '''目录顺不正常，按照序号count排序'''
        if enabel_digtes:
            all_page_links = sorted(all_page_links, key=lambda x: x[-1])

        PF.loggings.debug('The article list sort is complete')
        return all_page_links, len(all_page_links), ori_domain


def process(fx, link_list, var_args=None):
    """
    :param fx:          提取文本
    :param link_list:   页面URL总列表
    :param retry:       失败重试次数
    """

    PF.try_mkdir(PF.down_path)
    while link_list:
        pop = link_list.pop(0)      # 提取一条链接并从原始列表删除
        link = pop[0]              # url
        title = pop[1]               # title
        count = pop[2]
        try:
            page_text, title = fx(link, title, var_args)
        except BaseException as err:
            PF.loggings.error('URL{} requests failed, {} {} {}'.format(var_args.retry, title, link, str(err)))
            Error_url.append('requests failed ' + ' '.join([str(count), title, link, str(err)]))
        else:
            wr = PF.write_text(count, title, page_text, page_count)
            if wr is not True:
                Unable_write.append('Write failed ' + ' '.join([str(count), title, link, str(wr)]))


def multithreading():
    """
    页面处理多线程化
    """
    class mu_threading(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)
            self.daemon = True

        def run(self):
            process(extract_text, links, var_args=args)

    mu_list = []
    for num in range(os.cpu_count()*2):
        m = mu_threading()
        mu_list.append(m)
        m.start()           # 开始线程
    for mu in mu_list:
        mu.join()           # 等待所有线程完成
    PF.loggings.debug('Multi-threaded processing is complete! ')


class UrlAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        global html_url
        html_url = values[0]
        setattr(namespace, self.dest, values)


def args_parser():
    parse = argparse.ArgumentParser(description='文本下载器帮助',
                                    epilog='空参数将使用预定义的Url: %s' % html_url,
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ''''''
    parse_url_group = parse.add_mutually_exclusive_group()
    parse_url_group.add_argument('-c', metavar='catalog url', nargs=1, type=str, action=UrlAction,
                                 help='目录页地址，下载小说通常为所有章节的目录页url')
    parse_url_group.add_argument('-s', metavar='single url', nargs=1, type=str, action=UrlAction,
                                 help='文本页面URL, 抓取单一url的文本内容')
    ''''''
    parse.add_argument('-r', nargs=1, dest='retry', type=int, choices=range(0, 8), default=3, help='最大请求失败重试次数')

    parse.add_argument('-b', dest='block_size', type=int, choices=range(2, 10), default=5, help='文本行块分布函数块大小')

    parse.add_argument('-debug', nargs=1, type=int, choices=range(0, 4), default=1,
                       help='debug功能，0关闭，1输出到控制台，2输出到文件，3同时输出')

    switch_group = parse.add_argument_group(title='额外选项', description='打开或关闭对应功能')
    switch_group.add_argument('--drawing', action='store_const', const=True, default=False, help='绘制文本分布函数图')
    switch_group.add_argument('--delete-blank', dest='leave_blank', action='store_const', const=False,
                              default=True, help='删除文本中的空格，默认保留')
    switch_group.add_argument('--save-image', dest='image',action='store_const', const=True, default=False,
                              help='保留正文中的图片链接')
    switch_group.add_argument('--repeat', action='store_const', const=True, default=False,
                              help='启用循环过滤，默认关闭，只进行一次过滤')

    parse.add_argument('--version', action='version', version='%(prog)s 0.4', help='显示版本号')
    args_ = parse.parse_args()
    if args_.c is not None:args_.drawing = False
    print(args_)
    return args_

if __name__ == '__main__':
    args = args_parser()
    PF.init_logs(PF.loggings, args.debug)

    if args.s:
        page_count = 1
        process(fx=extract_text, link_list=[[html_url, '', 1000]], var_args=args)
    else:
        '''从目录页面提取所有章节URL'''
        links, page_count, domain = extract_url(html_url, retry=args.retry)
        PF.loggings.debug('chapter processing starts  ')
        '''多线程处理处理章节URL'''
        multithreading()
        # '''单线程处理章节URL列表'''
        # process(fx=extract_text, link_list=links, retry=retry_count)
        '''合并文本'''
        PF.text_merge(os.path.abspath('.'), count=page_count)

    if len(Unable_write) == 1 and len(Error_url) == 1:
        PF.loggings.debug('script complete, Everything OK!')
        sys.exit(0)
    PF.loggings.debug('script complete, EBut there are some errors :(')
    try:
        terminal_size = os.get_terminal_size().columns - 1
    except BaseException:
        terminal_size = 70
    PF.loggings.info('\n\n\n{}\n{}Error total:\n{}'.format('+' * terminal_size, ' ' * int(terminal_size / 2 - 5),
                                                           '+' * terminal_size))
    PF.loggings.info('# '.join(Error_url) + '# '.join(Unable_write))
    sys.exit(1)
