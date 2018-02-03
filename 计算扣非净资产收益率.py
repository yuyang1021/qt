'''
扣非净益率即扣除非正常损益后的净益率，其计算公式为：（净利润+非正常损益）/股东权益
本来我们的算法是连续三年里，取财报中每一年的扣非净益率和股东权益并相除。但除了计算每年的扣非净益率，我们希望算法可以根据季报计算多个季度的扣非净益率，以适用于更灵活的场景。改进后可以选取三段时间内的扣非净益率之和，并除以每段时间末的股东权益。
'''
import numpy as np
import pandas as pd
from jqdata import *
from datetime import datetime
import datetime as dt
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.finance import candlestick_ohlc

def back(x):
    if x[-1]=='1':
        return str(int(x[:4])-1)+'q4'
    else:
        return str(x[:5])+str(int(x[-1])-1)
    
today=datetime.strptime(str(datetime.now())[:10], '%Y-%m-%d')
def delta_days(x):
    d2=datetime.strptime(str(x)[:10], '%Y-%m-%d')
    return (today-d2).days

'''
q_end：截止时间，由这个时间向前推三个时间段。格式为'20xxqx'，表示某年第几个季度，例：'2016q3'
p3, p2, p1：由后至前的三个时间段分别覆盖了几个季度。例：3,4,5的输入方式表示最后一段时间覆盖3个季度(2015q4-2016q3)，中间一段覆盖4个季度(2014q4-2015q4)，第一段覆盖5个季度(2013q3-2014q4)。
r3, r2, r1：由后至前的三个时间段的收益率阈值，即这个时间段内的扣非净益率超过多少才会被留下。经验表明，一个年净利率取0.2比较合适，故前面p为4的话，对应r可取0.2左右。
date_for_index：根据指数选取指数所含股票的日期。日期不同，指数内包含的函数也不同。
样例：
举一个例子：函数输入的时间为2016q3，表示这三段时间的截止时间为2016年第三季度。为了确定三段时间的长度，需要依次输入p3, p2, p1，分别为第三段、第二段、第一段时间包括的季度数量。将每只股在这三个时间段内的扣非净利润加总，再除以每个时间段末的股东权益，就可以得到该公司在这一段时间内的扣非净益率了。
得到三段时间的扣非净益率后，我们根据需要，选取扣非净益率大于阈值的股票。三段时间的阈值也由我们手动输入，这里我们选取三段时间分别为3、4、4个季度，即三段时间由后向前覆盖的季度分别为：2015q4-2016q3、2014q4-2015q4、2013q4-2014q4。根据实验，我们将三段时间内的收益率阈值分别取为0.12,0.18,0.18。
'''

def cal_df(q_end,p3=4,p2=4,p1=4,r3=0.15,r2=0.15,r1=0.15,date_for_index='2017-12-31'):
    #选取上证综指和深证成指的全体股票
    g1=get_index_stocks('000001.XSHG',date=date_for_index)
    g2=get_index_stocks('399001.XSHE',date=date_for_index)
    stocks=g1+g2
    q1=query(indicator).filter(indicator.code.in_(stocks))
    q2=query(balance).filter(balance.code.in_(stocks))
    
    #计算第三段扣非净益率
    df=get_fundamentals(q1,statDate=q_end)[['code','adjusted_profit']]
    df=df.rename(columns={'adjusted_profit':'prof'+q_end})
    df.index=df['code'].values
    df_=get_fundamentals(q2,statDate=q_end)[['code','total_owner_equities']]
    df_.index=df_['code'].values
    df['equity'+q_end]=df_['total_owner_equities']
    q_date=q_end
    for i in range(p3-1):
        q_date=back(q_date)
        df_=get_fundamentals(q1,statDate=q_date)[['code','adjusted_profit']]
        df_.index=df_['code'].values
        df['prof'+q_end]=df['prof'+q_end]+df_['adjusted_profit']
    q_end3=q_end
    df['rate'+q_end3]=df['prof'+q_end3]/df['equity'+q_end3]
    
    #计算第二段扣非净益率
    q_end=back(q_date)
    df_=get_fundamentals(q1,statDate=q_end)[['code','adjusted_profit']]
    df_.index=df_['code'].values
    df['prof'+q_end]=df_['adjusted_profit']
    df_=get_fundamentals(q2,statDate=q_end)[['code','total_owner_equities']]
    df_.index=df_['code'].values
    df['equity'+q_end]=df_['total_owner_equities']
    q_date=q_end
    for i in range(p2-1):
        q_date=back(q_date)
        df_=get_fundamentals(q1,statDate=q_date)[['code','adjusted_profit']]
        df_.index=df_['code'].values
        df['prof'+q_end]=df['prof'+q_end]+df_['adjusted_profit']
    q_end2=q_end
    df['rate'+q_end2]=df['prof'+q_end2]/df['equity'+q_end2]    
    
    #计算第一段扣非净益率
    q_end=back(q_date)
    df_=get_fundamentals(q1,statDate=q_end)[['code','adjusted_profit']]
    df_.index=df_['code'].values
    df['prof'+q_end]=df_['adjusted_profit']
    df_=get_fundamentals(q2,statDate=q_end)[['code','total_owner_equities']]
    df_.index=df_['code'].values
    df['equity'+q_end]=df_['total_owner_equities']
    q_date=q_end
    for i in range(p1-1):
        q_date=back(q_date)
        df_=get_fundamentals(q1,statDate=q_date)[['code','adjusted_profit']]
        df_.index=df_['code'].values
        df['prof'+q_end]=df['prof'+q_end]+df_['adjusted_profit']
    q_end1=q_end
    df['rate'+q_end1]=df['prof'+q_end1]/df['equity'+q_end1]
    
    #选取符合条件的股票
    df=df[(df['rate'+q_end1]>r1) & (df['rate'+q_end2]>r2) & (df['rate'+q_end3]>r3) 
          &(df['prof'+q_end1]>0)&(df['prof'+q_end2]>0)&(df['prof'+q_end3]>0)]
    df=df[['rate'+q_end3,'rate'+q_end2,'rate'+q_end1]]
    
    #对符合条件的股票进行处理
    #start_date:上市日期 days:上市天数 pe_ratio：当天的市盈率 market_cap：当天的市值
    sat_list=list(df.index)
    name_list=list(map(lambda x:get_security_info(x).display_name,sat_list))
    start_list=list(map(lambda x:get_security_info(x).start_date,sat_list))
    df.insert(0,'name',name_list)
    df['start_date']=start_list
    days_list=list(map(lambda x:delta_days(x),start_list))
    df['days']=days_list
    df=df.sort(columns='rate'+q_end3,ascending=False)
    q3=query(valuation).filter(valuation.code.in_(sat_list))
    fund=get_fundamentals(q3)[['code','pe_ratio','market_cap']]
    fund.index=fund['code'].values
    df['pe_ratio']=fund['pe_ratio']
    df['market_cap']=fund['market_cap']
    return df

'''
df：上一部分计算后得到的dataframe结果。
st_date, ed_date：画图选取的开始时间和结束时间。需要注意的是，如果将画图开始时间选得太早，有的股票可能还没上市，所以最好取2015年及其以后的日期作为开始时间。
freq：调取价格的频率，默认为5分钟一次。精度越高，对投资组合价格变动的刻画就越精确。
delta：画图时，K线图里每一个bar是由多少个价格画出来的。由于一天的交易时间是240分钟，故如果取freq=5m，一天就是48个价格。经验表明，若freq=5m，将delta取为240比较合适，大概需要跑1~2分钟。
'''
def draw_k(df,st_date,ed_date,freq='5m',delta=240):
    #获取需要使用的股票代码，并标记开始和结束的日期
    value_stocks=list(df.index)
    days=get_all_trade_days()
    trade_days=list(map(lambda x:str(x),days))
    for i in range(len(trade_days)):
        if trade_days[i]==st_date:
            day_flag1=i
        if trade_days[i]==ed_date:
            day_flag2=i
    
    #获取对应股票的价格，获取投资组合的价格情况
    prices=get_price(value_stocks,start_date=trade_days[day_flag1],end_date=trade_days[day_flag2],frequency=freq)
    prices['sum']=prices.sum(axis=1)
    close_=prices['close'].sum(axis=1).values
    open_=prices['open'].sum(axis=1).values
    high_=prices['high'].sum(axis=1).values
    low_=prices['low'].sum(axis=1).values
    volum_=prices['volume'].sum(axis=1).values

    closep=list(close_[delta*i+delta-1] for i in range(int(len(close_)/delta)))
    openp=list(close_[delta*i] for i in range(int(len(close_)/delta)))
    highp=list(max(close_[delta*i:delta*i+delta-1]) for i in range(int(len(close_)/delta)))
    lowp=list(min(close_[delta*i:delta*i+delta-1]) for i in range(int(len(close_)/delta)))
    volume=list(np.mean(close_[delta*i:delta*i+delta-1]) for i in range(int(len(close_)/delta)))

    x,y,candleAr=0,len(closep),[]
    date = np.linspace(0,y,y)
    while x < y:
        appendLine = date[x],openp[x],highp[x],lowp[x],closep[x],volume[x]
        candleAr.append(appendLine)
        x += 1
        
    #提取日期，绘制K线图横坐标
    quotes2=get_price('000001.XSHE', start_date=st_date, end_date=ed_date, frequency='daily',skip_paused=False)
    t = quotes2.index.values
    t1 = t[-len(t):].astype(dt.date)/1000000000
    ti=[]
    for i in range(int(len(t)/50)):
        a=i*50
        d = dt.date.fromtimestamp(t1[a])
        t2=d.strftime('$%Y-%m-%d$')
        ti.append(t2)
    d1= dt.date.fromtimestamp(t1[len(t)-1])
    d2=d1.strftime('$%Y-%m-%d$')
    ti.append(d2)
    
    #绘制K线图
    fig = plt.figure(figsize=(16, 8))
    ax1 = plt.subplot2grid((10,4),(0,0),rowspan=10,colspan=4)
    candlestick_ohlc(ax1, candleAr, width=0.5, colorup='r', colordown='g', alpha=0.6)
    ax1.set_xticks(np.linspace(-2,len(closep)+2,len(ti))) 
    ax1.set_xticklabels(ti)
    plt.setp(plt.gca().get_xticklabels(), rotation=45, horizontalalignment='right')
    plt.show()

df_use=cal_df('2016q3',3,4,4,0.12,0.18,0.18)
df_use
draw_k(df_use,'2015-01-05','2017-12-29')