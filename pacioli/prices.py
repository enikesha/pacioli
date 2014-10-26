# Copyright (c) 2014, Satoshi Nakamoto Institute
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
# 
# 3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import fnmatch
import io
from datetime import datetime, date, timezone
import time
import logging
import sys
import csv
import json
import uuid
from pacioli import app, db, models
from sqlalchemy.sql import func, extract
from sqlalchemy import exc
import subprocess

APP_ROOT = os.path.dirname(os.path.abspath(__file__))

def import_data(database):
    searchdir = os.path.join(APP_ROOT,'data_prices/')
    matches = []
    p = subprocess.call([
    'psql', database, '-U', 'pacioli',
    '-c', "DELETE FROM prices",'--set=ON_ERROR_STOP=true'
    ])
    p = subprocess.call([
    'psql', database, '-U', 'pacioli',
    '-c', "DELETE FROM price_feeds",'--set=ON_ERROR_STOP=true'
    ])
    for root, dirnames, filenames in os.walk('%s' % searchdir):
        for filename in fnmatch.filter(filenames, '*.csv'):
            matches.append(os.path.join(root,filename))
    for csvfile in matches:
        filename = csvfile.split("/")
        filename = filename[-1]
        p = subprocess.call([
        'psql', database, '-U', 'pacioli',
        '-c', "\COPY price_feeds(timestamp, price, volume) FROM %s HEADER CSV" % csvfile,
        '--set=ON_ERROR_STOP=true'
        ])
        p = subprocess.call([
        'psql', database, '-U', 'pacioli',
        '-c', "UPDATE price_feeds SET timestamp = cast(timestamp/100 as int)*100",'--set=ON_ERROR_STOP=true'
        ])
        p = subprocess.call([
        'psql', database, '-U', 'pacioli',
        '-c', "INSERT INTO prices SELECT timestamp,  '%s' AS source, 'USD' as currency, cast(((sum(price*volume) / sum(volume))*100) as int) AS rate FROM price_feeds WHERE volume > 0 GROUP BY timestamp" % filename,'--set=ON_ERROR_STOP=true'
        ])
        p = subprocess.call([
        'psql', database, '-U', 'pacioli',
        '-c', "DELETE FROM price_feeds",'--set=ON_ERROR_STOP=true'
        ])
        
    return True

def getRate(date):
    date = int(date.strftime('%s'))
    closest_price = db.session.query(models.Prices.rate).order_by(func.abs( date -  models.Prices.date)).first()
    return int(closest_price[0]/100)