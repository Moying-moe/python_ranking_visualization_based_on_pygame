import pygame
from pygame.locals import *
import sys
from random import randint
import os
import csv


#############################################
BLACK = 0,0,0
WHITE = 255,255,255
RED = 255,0,0
GREEN = 0,255,0
BLUE = 0,0,255
GREY = 128,128,128
DEEP_GREY = 40,40,40
#############################################
AXIS_WIDTH = 950
AXIS_HEIGHT = 600 #12
FADE_SPEED = 20
TEXT_TOP1_TIME = '霸榜天数   '
DATE_INTERVAL = 30 #ticks or frames 比如30=0.5s
TOP_NUM = 20 #显示多少个
BAR_HEIGHT = AXIS_HEIGHT // (TOP_NUM*1.5)
#############################################


def HSV2RGB(H, S, V):
    if S == 0:
        return V,V,V
    else:
        H /= 60
        i = int(H)
        f = H - i
        a = int(V * (1-S))
        b = int(V * (1-S*f))
        c = int(V * (1-S*(1-f)))
        if i == 0:
            return V,c,a
        elif i == 1:
            return b,V,a
        elif i == 2:
            return a,V,c
        elif i == 3:
            return a,b,V
        elif i == 4:
            return c,a,V
        elif i == 5:
            return V,a,b

def findname(ilist, value):
    for i in range(len(ilist)):
        if ilist[i].iname == value:
            return i
    return -1

class Bar:
    def __init__(self, iname, itype, ivalue):
        self.iname = iname
        self.itype = itype
        self.ivalue = ivalue
        self.lastvalue = ivalue
        self.color = HSV2RGB(randint(0,359),0.7,230)
        self.lastwidth = 0
        self.rank = 21
        self.lastrank = 21

    def get_pos(self, step, max_value):
        #需要返回的信息:顶端位置 宽度 数值 透明度 是否显示
        #顶部坐标计算公式：rank*BAR_HEIGHT*1.5
        if step == -1:
            top = int(self.rank*BAR_HEIGHT*1.5)
            if self.rank <= 20:
                alpha = 255
                show = True
            else:
                alpha = 0
                show = False
            value = self.ivalue
            width = (value/max_value)*AXIS_WIDTH
            return top, width, value, alpha, show
        if self.rank != self.lastrank:#有位置变化 需要计算位移和平滑数字
            start = self.lastrank*BAR_HEIGHT*1.5
            end = self.rank*BAR_HEIGHT*1.5
            top = int(start + (end-start)*(step/DATE_INTERVAL)) #return
            if self.rank > 20 and self.lastrank <= 20:#掉出榜面
                alpha = 255 * (1-step/DATE_INTERVAL)
                show = True
            elif self.rank <= 20 and self.lastrank > 20:#入榜
                alpha = 255 * (step/DATE_INTERVAL)
                show = True
            else:
                if self.rank <= 20:
                    alpha = 255
                    show = True
                else:
                    alpha = 0
                    show = False
        else:
            top = int(self.rank*BAR_HEIGHT*1.5) #return
            if self.rank <= 20:
                alpha = 255
                show = True
            else:
                alpha = 0
                show = False
        start = self.lastvalue
        end = self.ivalue
        value = start + (end-start)*(step/DATE_INTERVAL) #return
        start = self.lastwidth
        end = (end/max_value)*AXIS_WIDTH
        width = start + (end-start)*(step/DATE_INTERVAL) #return
        value = int(value)
        return top, width, value, alpha, show

class BarList:
    def __init__(self, ilist):
        self.data = ilist
        self.data.sort(key = lambda x: x.ivalue,reverse = True)
        for i in range(len(self.data)):
            self.data[i].lastrank = self.data[i].rank
            self.data[i].rank = i+1

    def update(self, data, max_value):
        for each in data:
            temp = findname(self.data,each['name'])
            if temp != -1:#有
                self.data[temp].lastvalue = self.data[temp].ivalue
                self.data[temp].lastwidth = (self.data[temp].ivalue/max_value)*AXIS_WIDTH
                self.data[temp].ivalue = each['value']
            else:
                self.data.append(Bar(each['name'],
                                     each['type'],
                                     each['value']))
        self.data.sort(key = lambda x: x.ivalue,reverse = True)
        for i in range(len(self.data)):
            self.data[i].lastrank = self.data[i].rank
            self.data[i].rank = i+1



def numstr(num):
    if num >= 100000000:
        if num % 100000000 == 0:
            return '%s亿'%(num//100000000)
        else:
            return '%.1f亿'%(num/100000000)
    elif num >= 10000:
        if num % 10000 == 0:
            return '%s万'%(num//10000)
        else:
            return '%.1f万'%(num/10000)
    else:
        return str(num)

'''
从板块上分为
√1.顶部信息栏 用于显示榜首信息、类型、霸榜时间
√2.坐标轴区 用于显示横向坐标轴
√3.柱状图区 用于显示柱状图和对应的纵向坐标轴信息以及数据
√4.时间区 用于显示当前时间

数据结构参考@Jannchie见齐 的结构
csv文件
4个key：name,type,value,date

变量存储方式：
使用一个字典，key为date
字典每一项的值为一个列表，列表由若干字典组成，key为name,type,value
'''
    

#坐标轴
def axis(max_value, min_limit, is_zero = True, min_value = 0):
    surface = pygame.surface.Surface((AXIS_WIDTH+60,AXIS_HEIGHT))
    surface.fill(WHITE)
    font = pygame.font.SysFont('SimHei',15)
    '''
    max_value: 最大值
    min_limit: 最小界限
    is_zero: 是否最左端始终为0
    min_value: 最小值（只有当is_zero==True时才生效）
'''
    #刻度密度可以有：1、2、5、（下一个循环）
    #如：1→2→5→10→20→50→100→200→500
    if is_zero:
        if max_value >= min_limit:
            temp = len(str(int(max_value)))
            #始终尝试 位数-1的最低刻度（1） 即10**(temp-1)
            for i in (1,2,5,10):
                if 6 <= max_value//(i*10**(temp-2)) <= 15:
                    kd = i*10**(temp-2)
                    num = max_value//kd
                    break
        else:
            temp = len(str(min_limit))
            for i in (1,2,5,10):
                if 6 <= min_limit//(i*10**(temp-2)) <= 15:
                    kd = i*10**(temp-2)
                    num = min_limit//kd
                    break
                
        global lastk
        if lastk != None and lastk < kd:
            global fadev
            fadev = FADE_SPEED
        lastk = kd

        if fadev != 0:
            fadev -= 1
        
        #fade
        if fadev != 0:
            if i == 5:
                fkd = 2*10**(temp-2)
            else:#1,2,5
                fkd = kd//2#1000→500 2000→1000 10000→5000
            fnum = max_value//fkd

        #fade
        if fadev != 0:
            for each in (x*fkd for x in range(fnum+1) if x*fkd not in (x*kd for x in range(num+1))):
                temp = (each/max_value)*AXIS_WIDTH+25
                color = 255-127*(fadev/FADE_SPEED)
                color = color,color,color
                pygame.draw.aaline(surface,color,(temp,0),(temp,AXIS_HEIGHT-30))
                tsur = font.render(numstr(each), True, color)
                tsur_r = tsur.get_rect()
                tsur_r.center = temp,AXIS_HEIGHT-15
                surface.blit(tsur,tsur_r)
        
        #max_value的宽度适中为AXIS_WIDTH 那么剩下来的刻度宽度就显而易见了
        for each in (x*kd for x in range(num+1)):
            temp = (each/max_value)*AXIS_WIDTH+25
            pygame.draw.aaline(surface,GREY,(temp,0),(temp,AXIS_HEIGHT-30))
            tsur = font.render(numstr(each), True, GREY)
            tsur_r = tsur.get_rect()
            tsur_r.center = temp,AXIS_HEIGHT-15
            surface.blit(tsur,tsur_r)

    return surface

#顶部信息
def top_bar(m_type, m_name, m_time):
    #从左到右依次是 type name time
    surface = pygame.surface.Surface((AXIS_WIDTH+60,80))
    surface.fill(WHITE)
    font = pygame.font.SysFont('SimHei',50)
    #font.set_bold(True)
    
    tsur = font.render(m_type,True,DEEP_GREY)
    surface.blit(tsur,(25,15))
    tsur = font.render(m_name,True,DEEP_GREY)
    surface.blit(tsur,(25+int(AXIS_WIDTH*0.3),15))
    tsur = font.render(TEXT_TOP1_TIME + str(m_time),True,DEEP_GREY)
    tsur_r = tsur.get_rect()
    tsur_r.right = AXIS_WIDTH+60
    tsur_r.top = 15
    surface.blit(tsur,tsur_r)
    return surface

#时间
def bottom_date(dates):
    font = pygame.font.SysFont('SimHei',70)
    tsur = font.render(dates,True,DEEP_GREY)
    return tsur

#柱状图
def bar_graph(surface, pos, data, step):
    #每个高度为AXIS_HEIGHT//30
    #柱与柱之间间隔为(AXIS_HEIGHT-(AXIS_HEIGHT//30)*count)//count
    '''

需要有以下要素：
1、一次INTERVAL中平滑变化顶端显示的数值
2、一次INTERVAL中平滑移动有变动排名的项目
'''
    font = pygame.font.SysFont('SimHei',int(BAR_HEIGHT)+2)
    font2 = pygame.font.SysFont('SimHei',int(BAR_HEIGHT)+8)
    global store
    for each in store.data:
        top, width, value, alpha, show = each.get_pos(step,store.data[0].ivalue)
        if show:
            #bar
            c = each.color[0],each.color[1],each.color[2],alpha
            pygame.draw.rect(surface,each.color,(pos[0]+1,pos[1]+top,width,BAR_HEIGHT))
            tsur = font.render(each.iname,True,each.color)
            tsur_r = tsur.get_rect()
            tsur_r.right, tsur_r.top = pos[0]-5, pos[1]+top-1
            surface.blit(tsur,tsur_r)
            
            tsur = font2.render(each.iname,True,each.color)
            tsur_r = tsur.get_rect()
            tsur_r.right, tsur_r.bottom = pos[0] + width, pos[1] + top + BAR_HEIGHT
            make_bold(surface,tsur,tsur_r)
            
            tsur = font2.render(each.iname,True,WHITE)
            surface.blit(tsur,tsur_r)
            
            tsur = font.render(str(value),True,each.color)
            surface.blit(tsur,(pos[0] + width + 5, pos[1] + top-1))
            
    
def make_bold(surface, tsur, rect):
    x, y = rect.left,rect.top
    surface.blit(tsur,(x-1,y-1))
    surface.blit(tsur,(x-1,y))
    surface.blit(tsur,(x-1,y+1))
    surface.blit(tsur,(x,y-1))
    surface.blit(tsur,(x,y))
    surface.blit(tsur,(x,y+1))
    surface.blit(tsur,(x+1,y-1))
    surface.blit(tsur,(x+1,y))
    surface.blit(tsur,(x+1,y+1))









path = input('请输入文件路径(如果在根目录下可以直接输入文件名):')
while not os.path.exists(path):
    print('路径错误')
    path = input('请输入文件路径(如果在根目录下可以直接输入文件名):')
with open(path) as f:
    data = list(csv.reader(f))[1:]
ranks = {}
for each in data:
    date = each[3]
    if date in ranks:
        ranks[date].append({'name':each[0],'type':each[1],'value':int(each[2])})
    else:
        ranks[date] = [{'name':each[0],'type':each[1],'value':int(each[2])}]
data = ranks

pygame.init()
screen = pygame.display.set_mode((1280,720)) #暂定
clock = pygame.time.Clock()

'''data = {'2010-08':[{'name':'A','type':'','value':1},
                   {'name':'B','type':'','value':2},
                   {'name':'C','type':'','value':3}],
        '2010-09':[{'name':'A','type':'','value':4},
                   {'name':'B','type':'','value':2},
                   {'name':'C','type':'','value':3}],
        '2010-10':[{'name':'A','type':'','value':5},
                   {'name':'B','type':'','value':3},
                   {'name':'C','type':'','value':4}],
        }'''

store = BarList([])
data_date = sorted(list(data)) #获得升序日期
index = 0
max_index = len(data_date)

fadev = 0
lastk = None
frame = -1
temp = sorted(data[data_date[0]],key = lambda x: x['value'],reverse=True)
lastmaxv = temp[0]['value']
store.update(data[data_date[0]],lastmaxv)
top1 = 0
lasttop1 = ''

while True:
    for event in pygame.event.get():
        if event.type == QUIT:
            pygame.quit()
            sys.exit()

    if index == -1:
        clock.tick(60)
        continue

    screen.fill(WHITE)

    frame += 1
    if frame == DATE_INTERVAL+1 and index != -1:
        frame = 0
        index += 1

    if frame == 0: #更新数据
        top1 += 1
        if index == max_index:
            store.update(data[data_date[max_index-1]],store.data[0].ivalue)
        else:
            store.update(data[data_date[index]],store.data[0].ivalue)


    maxv = store.data[0].ivalue
    maxv = int(lastmaxv + (maxv-lastmaxv)*(frame/DATE_INTERVAL))
    if frame == 30:
        lastmaxv = store.data[0].ivalue
    temp = axis(maxv, 10)
    axistemp = temp.get_rect()
    axistemp.left, axistemp.top = 150, 80
    axistemp = axistemp.right,axistemp.bottom
    screen.blit(temp,(150,80))

    if lasttop1 != store.data[0].iname:
        lasttop1 = store.data[0].iname
        top1 = 0
    ttype, tname = store.data[0].itype, lasttop1
    temp = top_bar(ttype,tname,top1)
    screen.blit(temp,(150,0))

    if index == max_index:
        temp = bottom_date(data_date[max_index-1])
    else:
        temp = bottom_date(data_date[index])
    temp_r = temp.get_rect()
    temp_r.center = axistemp[0]-35, 0
    temp_r.bottom = axistemp[1]-30
    screen.blit(temp,temp_r)

    if index == max_index:
        bar_graph(screen,(175,80),data[data_date[max_index-1]],-1)
        index = -1
    else:
        bar_graph(screen,(175,80),data[data_date[index]],frame)


    

    pygame.display.flip()
    clock.tick(60)
