# -*- encoding: utf-8 -*-
import sys, sqlite3
from xml.sax.saxutils import escape
conn = sqlite3.connect(sys.argv[1])
c = conn.cursor()
c.execute('select erbs.id,erbs.nome,operadoras.nome,erbs.longitude,erbs.latitude from erbs,operadoras where erbs.operadora=operadoras.id')
print('<?xml version="1.0" encoding="UTF-8"?>')
print('<kml xmlns="http://www.opengis.net/kml/2.2">')
print('<Document>')
print('<name>ERBs</name>')
print('<open>1</open>')
print('<description>Estações rádio base do Brasil</description>')
for row in c:
    print('<Placemark>')
    print('<name>%s</name>'%escape(row[1].encode('utf-8','ignore')))
    print('<description>%d %s</description>'%(int(row[0]),escape(row[2].encode('utf-8','ignore'))))
    print('<Point><coordinates>%.10f,%.10f</coordinates></Point>'%(row[3],row[4]))
    print('</Placemark>')
print('</Document>')
print('</kml>')
conn.close()
