# -*- coding: utf-8 -*-
"""
===============================================================================
Created on Sun Jan 29 18:30:55 2023

www.heliumquant.com

basic and simple market following indicator and 
signal generator for algo trading

based on the CsucsErtek modell of the Heliumquant project


@author: dakar13
===============================================================================
"""
import asyncio
import sys
from typing import Dict
from datetime import datetime, timedelta
import datetime
import time
import pandas as pd
import requests
import nest_asyncio
nest_asyncio.apply()

class csucs_ertek:
    def __init__(self, tav, lep, profit) :
        self.csucsMax = 0.1
        self.csucsMin = 0.1
        self.signalMax = False
        self.signalMin = False
        
        self.csucsTav = float(tav)
        self.csucsLep = float(lep)
        self.takeProfit =float(profit)
        self.maxQua = 1                 #--- maximum quantity of the position in the same direction
        self.stopLoss = -50.5
        self.trailingStop = 0         # mutato is the base of the traing stop system -> buy position: 100-trailingStop
        self.kotesDB = 1                # qua of each trade, basic qua before multiplication
        
        self.index =0.1                 #--- index price a bid, ask, last average
        self.mutato =0.1                # special indicator for this signal generator see below
        
        self.paperTrades = pd.DataFrame({'Symbol': pd.Series(dtype='str'),                      # list of created paper orders
                           'qua': pd.Series(dtype='float'),
                           'price': pd.Series(dtype='float'),
                           'user_tag': pd.Series(dtype='str'),
                           'modify_time': pd.Series(dtype='str'),
                           'value': pd.Series(dtype='float')
                           })
        self.paperTrades.style.format("{.2f")
        self.paperQua = 0
        self.paperPNL = float(0)
        self.paperOpen_PNL = float(0)

        # stat-----------------------------------------------------------------
        # maxPV, maxIdo, minIdo, maxDB, minDB -> avg of HHV

    async def start(self, instr) :
        self.signalMax = False
        self.signalMin = False
        if instr.last >1 and instr.ask >0 and instr.bid >0:
            self.index = (instr.ask+instr.bid+instr.last)/3
        elif  instr.last >0 and instr.ask == 0 and instr.bid == 0 :
            self.index = (instr.last)
        elif instr.last == 0 and instr.ask > 0 and instr.bid > 0 :
            self.index = (instr.ask+instr.bid)/2
        elif instr.bid >1 : self.index = (instr.bid)
        if self.index == 0.1 :
            pass
        else :
            self.csucsMax=self.index+self.csucsTav/2
            self.csucsMin=self.index-self.csucsTav/2

            self.mutato = round((((self.csucsMax-self.index)/(self.csucsTav))*(-100))+150,2);
            # indicator of the signal generator 100 is the middle value, 50<150 range

    async def szamol(self, instr) :
        if self.csucsMax == 0.1 and self.csucsMin == 0.1 :
           await self.start(instr)

        if instr.last >1 and instr.ask >0 and instr.bid >0:
            self.index = (instr.ask+instr.bid+instr.last)/3
        elif  instr.last > 0 and instr.ask == 0 and instr.bid == 0 :
            self.index = (instr.last)
        elif instr.last == 0 and instr.ask > 0 and instr.bid > 0 :
            self.index = (instr.ask+instr.bid)/2
        elif instr.bid >1 : self.index = (instr.bid)
        
        self.index = round(self.index,2)
        
        if self.index != 0.1 :
            if (self.index ) > self.csucsMax + self.csucsLep:
                self.csucsMax = (self.index)
                self.signalMax = True
                self.signalMin = False
                if self.csucsMax - self.csucsTav > self.csucsMin : self.csucsMin = self.csucsMax - self.csucsTav

                if abs(self.paperQua) < self.maxQua : # paper trade
                    list_row = [instr.symbol, 1 , self.index, "maxsignal", str(datetime.datetime.now()), instr.pointValue*self.index*-1 ]
                    self.paperTrades.loc[len(self.paperTrades)] = list_row
    
            if (self.index ) < self.csucsMin - self.csucsLep:
                self.csucsMin = (self.index)
                self.signalMin = True
                self.signalMax = False
                if self.csucsMin + self.csucsTav < self.csucsMax : self.csucsMax = self.csucsMin + self.csucsTav

                if abs(self.paperQua) < self.maxQua : # paper trade
                    list_row = [instr.symbol, -1 , self.index, "minsignal", str(datetime.datetime.now()), instr.pointValue*self.index*1 ]
                    self.paperTrades.loc[len(self.paperTrades)] = list_row

    
            if self.signalMax and self.csucsMax-self.csucsLep > self.index : self.signalMax = False
            if self.signalMin and self.csucsMin+self.csucsLep < self.index : self.signalMin = False
    
            self.mutato = round((((self.csucsMax-self.index)/(self.csucsTav))*(-100))+150,2);
            
        # paper trading------------------------------------------------------------
        self.paperOpen_PNL = 0
        self.paperQua = int(self.paperTrades['qua'].sum())
        if self.paperQua == 0 :
            self.paperPNL = round(self.paperTrades['value'].sum(),2)
        else :
            self.paperPNL = round(self.paperTrades['value'].sum()+instr.pointValue*self.index*self.paperQua,2)
            
            kotesAr = 0
            hossz = len(self.paperTrades['price'])-1
            for jj in range(abs(self.paperQua)) :
                kotesAr = kotesAr + self.paperTrades['price'].values[hossz-jj]
            kotesAr = kotesAr/abs(self.paperQua)
            self.paperOpen_PNL = round(( self.index - kotesAr) * self.paperQua*instr.pointValue,2)

            if self.paperOpen_PNL < self.stopLoss :
                list_row = [instr.symbol, self.paperQua*-1 , self.index, "zarasStop", str(datetime.datetime.now()), instr.pointValue*self.index*self.paperQua ]
                self.paperTrades.loc[len(self.paperTrades)] = list_row
            if self.paperOpen_PNL > self.takeProfit :
                list_row = [instr.symbol, self.paperQua*-1 , self.index, "zarasTake", str(datetime.datetime.now()), instr.pointValue*self.index*self.paperQua ]
                self.paperTrades.loc[len(self.paperTrades)] = list_row
            if (self.paperQua > 0 and self.mutato < 100-self.trailingStop) or (self.paperQua < 0 and self.mutato > 100+self.trailingStop) :
                list_row = [instr.symbol, self.paperQua*-1 , self.index, "zarasFordul", str(datetime.datetime.now()), instr.pointValue*self.index*self.paperQua ]
                self.paperTrades.loc[len(self.paperTrades)] = list_row
            

    def getSignalMax(self) : 
        signal = False
        if self.signalMax :signal = True
        self.signalMax = False
        return signal

    def getSignalMin(self) : 
        signal = False
        if self.signalMin :signal = True
        self.signalMin = False
        return signal
