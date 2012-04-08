# -*- encoding: utf-8 -*-
import re, sys, sqlite3
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

gridsize = 10        # (km)
earthrad = 6371.009  # mean Earth radius (km)

nome_popular_para_nome_empresa = [
    ('Vivo', r'^VIVO '),
    ('TIM', r'^TIM '),
    ('Oi', r'(BRASIL TELECOM|^TNL PCS) '),
    ('Claro', r'^(AMERICEL|CLARO) '),
    ('Sercomtel', r'^SERCOMTEL '),
    ('AEIOU', r'^UNICEL '),
    ('Nextel', r'^NEXTEL '),
    ('AmazoniaCelular', r'^AMAZONIA '),
]

def projy(lat):
    # Mercator projection in y of latitude (in degrees)
    lat = np.pi*lat/180.
    return np.log(np.tan(lat)+1./np.cos(lat))

def construct_cmap(gridmax):
    lcmap = np.zeros((gridmax+1,3))
    lcmap[0] = np.array([0xbf,0xd1,0xd4])/256.
    for i in xrange(1,gridmax+1):
        lcmap[i] = np.array([np.log(i)/np.log(gridmax), 0., 0.])
    return ListedColormap(lcmap)

def main():
    conn = sqlite3.connect(sys.argv[1])
    
    c = conn.cursor()
    c.execute('select id, nome from operadoras;')
    operadoras = c.fetchall()
    
    for nome, regex_empresa in nome_popular_para_nome_empresa:
        opids = [opid for opid, nome_empresa in operadoras if re.search(regex_empresa, nome_empresa)]
        if len(opids) == 0:
            continue
        
        print(repr((nome, regex_empresa, opids)))
        
        c = conn.cursor()
        c.execute('select min(longitude),max(longitude),min(latitude),max(latitude) from erbs;')
        longmin,longmax,latmin,latmax = c.fetchone()
        print(repr((longmin,longmax,latmin,latmax)))
        
        xmin,xmax = longmin,longmax
        ymin,ymax = map(projy, [latmin,latmax])
        
        xdist = np.pi*(longmax-longmin)*earthrad/180.
        ydist = np.pi*(latmax -latmin )*earthrad/180.
        
        w,h = [1+int(np.floor(dist/gridsize)) for dist in (xdist,ydist)]
        print(repr((w,h)))
        
        xfac = float(xdist/gridsize)/(xmax-xmin)
        yfac = float(ydist/gridsize)/(ymax-ymin)
        
        grid = np.zeros((h,w), dtype=int)
        
        c = conn.cursor()
        c.execute('select longitude,latitude from erbs where operadora in (%s);'%','.join(map(str,opids)))
        for longitude,latitude in c:
            x,y = longitude, projy(latitude)
            x = int(np.floor(xfac*(x-xmin)))
            y = int(np.floor(yfac*(y-ymin)))
            grid[y,x] += 1
    
        gridmax = grid.max().max()
        print(repr(gridmax))
        
        lcmap = construct_cmap(gridmax)
        plt.imsave('operadoras/%s.png'%nome, grid, cmap=lcmap, origin='lower')
        #plt.imshow(grid, cmap=lcmap, origin='lower')
        #plt.show()
        
    conn.close()

if __name__ == '__main__':
    try:
        import psyco
        psyco.full()
    except:
        pass
    main()
