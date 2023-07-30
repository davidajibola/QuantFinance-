

import seaborn as sns
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.pyplot as plt2
import pandas as pd
from pandas import datetime
import math, time
import itertools
from sklearn import preprocessing
import datetime
from sklearn.metrics import mean_squared_error
from math import sqrt
from keras.models import Sequential
from keras.layers.core import Dense, Dropout, Activation
from keras.layers.recurrent import LSTM
from keras.models import load_model
from keras.utils import plot_model
from keras import backend as K
from keras.layers.convolutional import Convolution1D, MaxPooling1D
from keras.layers.core import Flatten
import keras
import h5py
import os
import graphviz
import pydot
from statistics import mean
import matplotlib.pyplot as plt
from mosek.fusion import *
from keras.utils.vis_utils import plot_model

seq_len = 72
shape = [seq_len, 19, 1]
neurons = [256, 256, 32, 1]
dropout = 0.3
decay = 0.3
epochs = 50
os.chdir("/Users/youssefberrada/Dropbox (MIT)/15.961 Independant Study/Data")
#os.chdir("/Users/michelcassard/Dropbox (MIT)/15.960 Independant Study/Data")
file = 'FX-5-merg.xlsx'
# Load spreadsheet
xl = pd.ExcelFile(file)
close = pd.ExcelFile('close.xlsx')
df_close=np.array(close.parse(0))


def get_stock_data(stock_name, ma=[],bollinger=[],exp_ma=[],ma_conv=[]):
    """
    Return a dataframe of that stock and normalize all the values. 
    (Optional: create moving average)
    
    """
    df = xl.parse(stock_name)
    #df.drop(['VOLUME'], 1, inplace=True)
    df.set_index('Date', inplace=True)
    
    # Renaming all the columns so that we can use the old version code
    df.rename(columns={'OPEN': 'Open', 'HIGH': 'High', 'LOW': 'Low', 'NUMBER_TICKS': 'Volume', 'LAST_PRICE': 'Adj Close'}, inplace=True)
     # Percentage change
    df['Pct'] = df['Adj Close'].pct_change()
    df.dropna(inplace=True)
    
    # Moving Average    
    if ma != []:
        for moving in ma:
            df['{}ma'.format(moving)] = df['Adj Close'].rolling(window=moving).mean()
    # Bollinger   
    if bollinger != []:
        def bbands(price, length=30, numsd=2):
            """ returns average, upper band, and lower band"""
            ave = pd.stats.moments.rolling_mean(price,length)
            sd = pd.stats.moments.rolling_std(price,length)
            upband = ave + (sd*numsd)
            dnband = ave - (sd*numsd)
            return np.round(upband,3), np.round(dnband,3)
        for moving in bollinger:
            df['{}bollingerup'.format(moving)],df['{}bollingerdown'.format(moving)] = bbands(df['Adj Close'], length=moving, numsd=2)
        
    # Exponential Moving Average    
    if exp_ma != []:
        for moving in exp_ma:
            df['{}exp_ma'.format(moving)] = df['Adj Close'].ewm(min_periods=1, adjust=True,com=moving).mean()
   
    # Moving Average Convergence   
    if ma_conv!= []:
        for moving in ma_conv:
            df['{}ma_conv'.format(moving)] = df['Adj Close'].ewm(min_periods=1, adjust=True,com=moving[0]).mean()-df['Adj Close'].ewm(min_periods=1, adjust=True,com=moving[1]).mean()
    
    
    
    df.dropna(inplace=True)
    
  
    # Move Adj Close to the rightmost for the ease of training
    adj_close = df['Adj Close']
    df.drop(labels=['Adj Close'], axis=1, inplace=True)
    df = pd.concat([df, adj_close], axis=1)
      
    return df


def plot_stock(df):
    print(df.head())
    plt.subplot(211)
    plt.plot(df['Adj Close'], color='red', label='Adj Close')
    plt.legend(loc='best')
    plt.subplot(212)
    plt.plot(df['Pct'], color='blue', label='Percentage change')
    plt.legend(loc='best')
    plt.show()


def load_data(stock,normalize,seq_len,split,ma=[],bollinger=[],exp_ma=[],ma_conv=[]):
    amount_of_features = len(stock.columns)
    print ("Amount of features = {}".format(amount_of_features))
    sequence_length = seq_len+1
    result_train = []
    result_test= []
    row = round(split * stock.shape[0])
    df_train=stock[0:row].copy()
    print ("Amount of training data = {}".format(df_train.shape[0]))
    df_test=stock[row:len(stock)].copy()
    print ("Amount of testing data = {}".format(df_test.shape[0]))


    if normalize:
        #Training
        min_max_scaler = preprocessing.MinMaxScaler()
        min_max_scaler.fit(df_train['Adj Close'].values.reshape(-1,1))
        df_train['Open'] = min_max_scaler.transform(df_train['Open'].values.reshape(-1,1))
        df_train['High'] = min_max_scaler.transform(df_train['High'].values.reshape(-1,1))
        df_train['Low'] = min_max_scaler.transform(df_train['Low'].values.reshape(-1,1))
        df_train['Adj Close'] = min_max_scaler.transform(df_train['Adj Close'].values.reshape(-1,1))
        df_train['Volume'] = min_max_scaler.fit_transform(df_train.Volume.values.reshape(-1,1))
        df_train['Pct'] = min_max_scaler.fit_transform(df_train['Pct'].values.reshape(-1,1))
        if ma != []:
            for moving in ma:
                df_train['{}ma'.format(moving)] = min_max_scaler.fit_transform(df_train['{}ma'.format(moving)].values.reshape(-1,1))
        if bollinger != []:
            for moving in bollinger:
                df_train['{}bollingerup'.format(moving)] = min_max_scaler.fit_transform(df_train['{}bollingerup'.format(moving)].values.reshape(-1,1))
                df_train['{}bollingerdown'.format(moving)] = min_max_scaler.fit_transform(df_train['{}bollingerdown'.format(moving)].values.reshape(-1,1))
        if exp_ma != []:
            for moving in exp_ma:
                df_train['{}exp_ma'.format(moving)] = min_max_scaler.fit_transform(df_train['{}exp_ma'.format(moving)].values.reshape(-1,1))
        if ma_conv!= []:
            for moving in ma_conv:
                df_train['{}ma_conv'.format(moving)] = min_max_scaler.fit_transform(df_train['{}ma_conv'.format(moving)].values.reshape(-1,1))
                
        #Test
        min_max_scaler.fit(df_test['Adj Close'].values.reshape(-1,1))
        df_test['Open'] = min_max_scaler.transform(df_test['Open'].values.reshape(-1,1))
        df_test['High'] = min_max_scaler.transform(df_test['High'].values.reshape(-1,1))
        df_test['Low'] = min_max_scaler.transform(df_test['Low'].values.reshape(-1,1))
        df_test['Adj Close'] = min_max_scaler.transform(df_test['Adj Close'].values.reshape(-1,1))
        df_test['Volume'] = min_max_scaler.fit_transform(df_test.Volume.values.reshape(-1,1))
        df_test['Pct'] = min_max_scaler.fit_transform(df_test['Pct'].values.reshape(-1,1))
        if ma != []:
            for moving in ma:
                df_test['{}ma'.format(moving)] = min_max_scaler.fit_transform(df_test['{}ma'.format(moving)].values.reshape(-1,1))
        if bollinger != []:
            for moving in bollinger:
                df_test['{}bollingerup'.format(moving)] = min_max_scaler.fit_transform(df_test['{}bollingerup'.format(moving)].values.reshape(-1,1))
                df_test['{}bollingerdown'.format(moving)] = min_max_scaler.fit_transform(df_test['{}bollingerdown'.format(moving)].values.reshape(-1,1))
        if exp_ma != []:
            for moving in exp_ma:
                df_test['{}exp_ma'.format(moving)] = min_max_scaler.fit_transform(df_test['{}exp_ma'.format(moving)].values.reshape(-1,1))
        if ma_conv!= []:
            for moving in ma_conv:
                df_test['{}ma_conv'.format(moving)] = min_max_scaler.fit_transform(df_test['{}ma_conv'.format(moving)].values.reshape(-1,1))
                
    #Training
    data_train = df_train.as_matrix()
    for index in range(len(data_train) - sequence_length):
        result_train.append(data_train[index: index + sequence_length])
    train = np.array(result_train)
    X_train = train[:, :-1].copy() # all data until day m
    y_train = train[:, -1][:,-1].copy() # day m + 1 adjusted close price

    #Test
    data_test = df_test.as_matrix()
    for index in range(len(data_test) - sequence_length):
        result_test.append(data_test[index: index + sequence_length])
    test = np.array(result_test)
    X_test = test[:, :-1].copy()
    y_test = test[:, -1][:,-1].copy()


    X_train = np.reshape(X_train, (X_train.shape[0], X_train.shape[1], amount_of_features))
    X_test = np.reshape(X_test, (X_test.shape[0], X_test.shape[1], amount_of_features))

    return [X_train, y_train, X_test, y_test]


def build_model(shape, neurons, dropout, decay):
    model = Sequential()

    model.add(LSTM(neurons[0], input_shape=(shape[0], shape[1]), return_sequences=True))
    model.add(Dropout(dropout))

    model.add(LSTM(neurons[1], input_shape=(shape[0], shape[1]), return_sequences=False))
    model.add(Dropout(dropout))

    model.add(Dense(neurons[2],kernel_initializer="uniform",activation='relu'))
    model.add(Dense(neurons[3],kernel_initializer="uniform",activation='linear'))

    adam = keras.optimizers.Adam(decay=decay)
    model.compile(loss='mse',optimizer='adam', metrics=['accuracy'])
    model.summary()
    return model


def build_model_CNN(shape, neurons, dropout, decay):
    model = Sequential()
    model.add(Convolution1D(input_shape = (shape[0], shape[1]), 
                        nb_filter=64,
                        filter_length=2,
                        border_mode='valid',
                        activation='relu',
                        subsample_length=1))
    model.add(MaxPooling1D(pool_length=2))

    model.add(Convolution1D(input_shape = (shape[0], shape[1]), 
                        nb_filter=64,
                        filter_length=2,
                        border_mode='valid',
                        activation='relu',
                        subsample_length=1))
    model.add(MaxPooling1D(pool_length=2))

    model.add(Dropout(0.25))
    model.add(Flatten())

    model.add(Dense(250))
    model.add(Dropout(0.25))
    model.add(Activation('relu'))

    model.add(Dense(1))
    model.add(Activation('linear'))
    adam = keras.optimizers.Adam(decay=decay)
    model.compile(loss='mse',optimizer='adam', metrics=['accuracy'])
    model.summary()
    return model

model = build_model_CNN(shape, neurons, dropout, decay)

plot_model(model, to_file='model_plot.png', show_shapes=True, show_layer_names=True)

def model_score(model, X_train, y_train, X_test, y_test):
    trainScore = model.evaluate(X_train, y_train, verbose=0)
    print('Train Score: %.5f MSE (%.2f RMSE)' % (trainScore[0], math.sqrt(trainScore[0])))

    testScore = model.evaluate(X_test, y_test, verbose=0)
    print('Test Score: %.5f MSE (%.2f RMSE)' % (testScore[0], math.sqrt(testScore[0])))
    return trainScore[0], testScore[0]

def percentage_difference(model, X_test, y_test):
    percentage_diff=[]

    p = model.predict(X_test)
    for u in range(len(y_test)): # for each data index in test data
        pr = p[u][0] # pr = prediction on day u

        percentage_diff.append((pr-y_test[u]/pr)*100)
    print(mean(percentage_diff))
    return p



def plot_result_norm(stock_name, normalized_value_p, normalized_value_y_test):
    newp=normalized_value_p
    newy_test=normalized_value_y_test
    plt2.plot(newp, color='red', label='Prediction')
    plt2.plot(newy_test,color='blue', label='Actual')
    plt2.legend(loc='best')
    plt2.title('The test result for {}'.format(stock_name))
    plt2.xlabel('5 Min ahead Forecast')
    plt2.ylabel('Price')
    plt2.show()


def denormalize(stock_name, normalized_value,split=0.7,predict=True):
    """
    Return a dataframe of that stock and normalize all the values. 
    (Optional: create moving average)
    """
    df = xl.parse(stock_name)
    #df.drop(['VOLUME'], 1, inplace=True)
    df.set_index('Date', inplace=True)
    
    # Renaming all the columns so that we can use the old version code
    df.rename(columns={'OPEN': 'Open', 'HIGH': 'High', 'LOW': 'Low', 'NUMBER_TICKS': 'Volume', 'LAST_PRICE': 'Adj Close'}, inplace=True)


    df.dropna(inplace=True)
    df = df['Adj Close'].values.reshape(-1,1)
    normalized_value = normalized_value.reshape(-1,1)
    
    row = round(split * df.shape[0]) 
    if predict:
        df_p=df[0:row].copy()
    else:
        df_p=df[row:len(df)].copy()
    
    #return df.shape, p.shape
    max_df=np.max(df_p)
    min_df=np.min(df_p)
    new=normalized_value*(max_df-min_df)+min_df
      
    return new

def portfolio(currency_list,file = 'FX-5-merg.xlsx',seq_len = 144,shape = [seq_len, 19, 1],neurons = [256, 256, 32, 1],dropout = 0.3,decay = 0.5,
              epochs = 90,ma=[50, 100, 200],bollinger=[50, 100, 200],exp_ma=[50, 100, 200],ma_conv=[[26,12]],split=0.7):
    i=0
    mini=99999999
    for currency in currency_list:
        df=get_stock_data(currency, ma,bollinger,exp_ma,ma_conv)
        X_train, y_train, X_test, y_test = load_data(df,True,seq_len,split,ma,bollinger,exp_ma,ma_conv)
        model = build_model_CNN(shape, neurons, dropout, decay)
        model.fit(X_train,y_train,batch_size=512,epochs=epochs,validation_split=0.3,verbose=1)
        p = percentage_difference(model, X_test, y_test)
        newp = denormalize(currency, p,predict=True)
        if mini>p.size:
            mini=p.size
        if i==0:
            predict=newp.copy()
        else:
            predict=np.hstack((predict[0:mini],newp[0:mini]))
        i+=1
    return predict



currency_list=[ 'GBP Curncy',
 'JPY Curncy',
 'EUR Curncy',
 'CAD Curncy',
 'NZD Curncy',
 'SEK Curncy',
 'AUD Curncy',
 'CHF Curncy',
 'NOK Curncy',
 'ZAR Curncy']
predictcur=portfolio(currency_list,file = 'FX-5-merg.xlsx',seq_len = seq_len,shape = [seq_len, 19, 1],neurons = [256, 256, 32, 1],dropout = 0.2,decay = decay,
              epochs = 50,ma=[12, 72, 144],bollinger=[12, 72, 144],exp_ma=[12, 72, 144],ma_conv=[[26,12]],split=0.7)

def MarkowitzWithTransactionsCost(n,mu,GT,x0,w,gamma,f,g):
    # Upper bound on the traded amount
    w0 = w+sum(x0)
    u = n*[w0]

    with Model("Markowitz portfolio with transaction costs") as M:
        #M.setLogHandler(sys.stdout)

        # Defines the variables. No shortselling is allowed.
        x = M.variable("x", n, Domain.greaterThan(0.0))
        #x = M.variable("x", n, Domain.lessThan(0.0))
        #x = M.variable("x", n, Domain.inRange(-3., 3.))
        
        # Additional "helper" variables 
        z = M.variable("z", n, Domain.unbounded())   
        # Binary variables
        y = M.variable("y", n, Domain.binary())

        #  Maximize expected return
        M.objective('obj', ObjectiveSense.Maximize, Expr.dot(mu,x))

        # Invest amount + transactions costs = initial wealth
        M.constraint('budget', Expr.add([ Expr.sum(x), Expr.dot(f,y),Expr.dot(g,z)] ), Domain.equalsTo(w0))

        # Imposes a bound on the risk
        M.constraint('risk', Expr.vstack( gamma,Expr.mul(GT,x)), Domain.inQCone())

        # z >= |x-x0| 
        M.constraint('buy', Expr.sub(z,Expr.sub(x,x0)),Domain.greaterThan(0.0))
        M.constraint('sell', Expr.sub(z,Expr.sub(x0,x)),Domain.greaterThan(0.0))
        # Alternatively, formulate the two constraints as
        #M.constraint('trade', Expr.hstack(z,Expr.sub(x,x0)), Domain.inQcone())

        # Constraints for turning y off and on. z-diag(u)*y<=0 i.e. z_j <= u_j*y_j
        M.constraint('y_on_off', Expr.sub(z,Expr.mulElm(u,y)), Domain.lessThan(0.0))

        # Integer optimization problems can be very hard to solve so limiting the 
        # maximum amount of time is a valuable safe guard
        M.setSolverParam('mioMaxTime', 10000.0) 
        M.solve()

        return (np.dot(mu,x.level()), x.level())

def rebalance(n,previous_prices,x0,w,mu,gamma=1):
    GT=np.cov(previous_prices)
    f = n*[0.00]
    g = n*[0.005]
    weights=MarkowitzWithTransactionsCost(n,mu,GT,x0,w,gamma,f,g)
    return weights


# Backtesting using rebalancing function for weights
def log_diff(data):
    return np.diff(np.log(data))


def backtest(prices, predictions, initial_weights):
    t_prices = len(prices[1,:])
    t_predictions = len(predictions)
    length_past = t_prices - t_predictions
    returns = np.apply_along_axis(log_diff, 1, prices)
    prediction_return = []
    port_return=1
    for k in range(t_predictions):
        prediction_return.append(np.log(predictions[k]/prices[:,length_past+k-1]))
    weights = initial_weights
    portfolio_return = []
    prev_weight = weights
    for i in range(0,t_predictions-1):
    #for i in range(0,1000):
        predicted_return = prediction_return[i]
        #predicted_return = returns[:,length_past+i-1]
        previous_return = returns[:,length_past+i-1]
        previous_returns = returns[:,0:(length_past+i-1)]
        if i==0:
            new_weight = rebalance(10,previous_returns,mu=predicted_return.tolist(),x0=prev_weight,w=0,gamma=5)
        else:
            new_weight = rebalance(10,previous_returns,mu=predicted_return.tolist(),x0=prev_weight,w=0,gamma=5)
        period_return = np.dot(new_weight,returns[:,length_past+i])
        port_return=port_return*(1+period_return)
        portfolio_return.append(port_return)
        prev_weight = new_weight
        print(period_return)
    return portfolio_return



x=backtest(df_close.T, predictcur, np.repeat(1/10,10))

plt.plot(x)
x[-1]

def plot_result(stock_name, normalized_value_p, normalized_value_y_test):
    newp = denormalize(stock_name, normalized_value_p,predict=True)
    newy_test = denormalize(stock_name, normalized_value_y_test,predict=False)
    plt2.plot(newp, color='red', label='Prediction')
    plt2.plot(newy_test,color='blue', label='Actual')
    plt2.legend(loc='best')
    plt2.title('The test result for {}'.format(stock_name))
    plt2.xlabel('5 Min ahead Forecast')
    plt2.ylabel('Price')
    plt2.show()
