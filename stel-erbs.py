# -*- encoding: utf-8 -*-
import sys, time, re, urllib2, cookielib, sqlite3, traceback
from urllib import urlencode

estados = [( 1, 'AC'), ( 2, 'AL'), ( 3, 'AM'), ( 4, 'AP'), ( 5, 'BA'), ( 6, 'CE'), ( 7, 'DF'), ( 8, 'ES'),
           ( 9, 'GO'), (10, 'MA'), (11, 'MG'), (12, 'MS'), (13, 'MT'), (14, 'PA'), (15, 'PB'), (16, 'PE'),
           (17, 'PI'), (18, 'PR'), (19, 'RJ'), (20, 'RN'), (21, 'RO'), (22, 'RR'), (23, 'RS'), (24, 'SC'),
           (25, 'SE'), (26, 'SP'), (27, 'TO')]

tela_url = 'http://sistemas.anatel.gov.br/stel/consultas/ListaEstacoesLocalidade/tela.asp?pNumServico=010'
server_encoding = 'iso-8859-1'

def criar_db():
    filename = time.strftime('erbs-%F-%H-%M.db')
    conn = sqlite3.connect(filename)
    conn.executescript("""
        pragma foreign_keys=on;
        create table estados(id integer primary key, uf text);
        create table municipios(id integer primary key, nome text, estado integer references estados(id) on delete restrict on update cascade, unique (nome, estado));
        create table operadoras(id integer primary key, cnpj text unique, nome text);
        create table erbs(id integer primary key, operadora integer references operadoras(id) on delete restrict on update cascade, nome text, municipio integer references municipios(id) on delete restrict on update cascade, bairro text, logradouro text, latitude real, longitude real, data_cadastro text, data_primeira_licenca text, data_ultima_licenca text);
    """)
    c = conn.cursor()
    for (estado_id, uf) in estados:
        c.execute('insert into estados values (?, ?);', (estado_id, uf))
    wait_commit(conn)
    return conn

def open_read(opener, fullurl, data=None):
    done = False
    while not done:
        try:
            f = opener.open(fullurl, data)
            data = f.read()
            f.close()
            done = True
        except:
            traceback.print_exc()
            done = False
    return data

def iniciar_opener():
    jar = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(jar))
    opener.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; pt-BR; rv:1.9.2.13) Gecko/20101206 Ubuntu/10.10 (maverick) Firefox/3.6.13')]
    open_read(opener, tela_url)
    return opener

def wait_commit(conn):
    done = False
    while not done:
        try:
            conn.commit()
            done = True
        except:
            traceback.print_exc()
            done = False

def processar_estado(conn, opener, estado_id, uf):
    print(repr(('processar_estado', estado_id, uf)))
    data = urlencode([('acao', 'C'),
                      ('pNumServico', '010'),
                      ('pSiglaUF', uf)])
    data = open_read(opener, tela_url, data)
    for entidade in set(re.findall(r'ConsultaEntidade\((\d+)\)', data)):
        processar_entidade(conn, opener, entidade, estado_id, uf)
        
def processar_entidade(conn, opener, entidade, estado_id, uf):
    print(repr(('processar_entidade', entidade, estado_id, uf)))
    qtde_estacoes = 1
    operadora_id = None
    operadora = None
    cnpj = None
    param = {
        'acao': 'C',
        'pNumServico': '010',
        'pSiglaUF': uf,
        'EntidadePar': entidade,
        'TotalPaginacao': 0
    }
    while qtde_estacoes > 0:
        print(repr(('processar_entidade', 'pagina', operadora_id, operadora, qtde_estacoes, param)))
        old_param = dict(param)
        try:
            url = tela_url
            if operadora != None:
                url += '&acao=C&chave=&hdnbutton=p'
            data = open_read(opener, url, urlencode(param)).decode(server_encoding, 'ignore')
            if operadora == None:
                operadora = re.search(ur'<label id="labelNúmero/Nome" >\d+ - (.+)', data).group(1).strip()
                cnpj = re.search(ur'<label id="labelCNPJ/CPF" >(\d+)', data).group(1).strip()
                c = conn.cursor()
                c.execute('select id from operadoras where cnpj=?', (cnpj,))
                operadora_id = c.fetchone()
                if operadora_id:
                    operadora_id, = operadora_id
                else:
                    c.execute('insert into operadoras (cnpj, nome) values (?, ?)', (cnpj, operadora))
                    wait_commit(conn)
                    operadora_id = c.lastrowid
                    print(repr(('processar_entidade', 'operadora adicionada', operadora_id, operadora, cnpj)))
            qtde_estacoes = int(re.search(ur'name="QtdeEstacoes" id="QtdeEstacoes" value="(\d+)"', data).group(1))
            data = data[data.index(u'<label>Última Licença</label>'):]
            i = data.index(u'</table>')
            rodape = data[i:]
            data   = data[:i]
            for m in re.finditer(ur'<input type="hidden" name="(.+?)" id="(.+?)" value="(.*?)"', rodape):
                param[m.group(1).encode(server_encoding, 'ignore')] = m.group(3).encode(server_encoding, 'ignore')
            municipio_id = None
            municipio = None
            while True:
                i = data.find('<tr >')
                if i < 0: break
                data = data[i+5:]
                entrydata = [m.group(1) for m in re.finditer(ur'<label>(.*?)</label>', data[:data.index(u'</tr>')])]
                entrydata = [x.replace('&nbsp;','').strip() for x in entrydata]
                if entrydata[3] != municipio:
                    municipio = entrydata[3]
                    c = conn.cursor()
                    c.execute('select id from municipios where nome=? and estado=?', (municipio, estado_id))
                    municipio_id = c.fetchone()
                    if municipio_id:
                        municipio_id, = municipio_id
                    else:
                        c.execute('insert into municipios (nome, estado) values (?, ?)', (municipio, estado_id))
                        wait_commit(conn)
                        municipio_id = c.lastrowid
                        print(repr(('processar_entidade', 'municipio adicionado', municipio_id, municipio, uf)))
                c = conn.cursor()
                while len(entrydata) < 11:
                    entrydata.append(u'')
                entrydata = (entrydata[0],            # id
                             operadora_id,            # operadora
                             entrydata[1],            # nome
                             municipio_id,            # municipio
                             entrydata[4],            # bairro
                             entrydata[5],            # logradouro
                             convll(entrydata[ 6]),   # latitude
                             convll(entrydata[ 7]),   # longitude
                             convd (entrydata[ 8]),   # data_cadastro
                             convd (entrydata[ 9]),   # data_primeira_licenca
                             convd (entrydata[10]),   # data_ultima_licenca
                            )
                c.execute('insert into erbs values (?,?,?,?,?,?,?,?,?,?,?)', entrydata)
                wait_commit(conn)
        except:
            traceback.print_exc()
            print('retrying')
            qtde_estacoes = 1
            param = dict(old_param)

def convll(ll):
    graus,direcao,minutos,segundos = re.match(ur'(\d{2})([NSEW])(\d{2})(\d{4})', ll).groups()
    graus  = float(graus)
    graus += float(minutos)/60.
    graus += float(segundos)/100./3600.
    if direcao in ('S','W'):
        graus = -graus
    return graus

def convd(d):
    if d == u'': return u''
    dia,mes,ano = [int(x) for x in re.match(ur'(\d+)/(\d+)/(\d+)', d).groups()]
    return u'%04d-%02d-%02d' % (ano,mes,dia)
            
def main():
    conn = criar_db()
    opener = iniciar_opener()
    for (estado_id, uf) in estados:
        processar_estado(conn, opener, estado_id, uf)
    conn.close()

if __name__ == '__main__':
    try:
        import psyco
        psyco.full()
    except: pass
    main()
