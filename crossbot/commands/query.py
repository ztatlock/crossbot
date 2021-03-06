from crossbot.commands import sql
import sqlite3
from datetime import datetime
import crossbot
from multiprocessing import Pool, TimeoutError

def init(client):
    parser = client.parser.subparsers.add_parser('query', help='Run a saved query')
    parser.set_defaults(command=query)

    parser.add_argument('name', nargs='?', help='Stored query name to run')
    parser.add_argument('--save', action='store_true', help='Create or overwrite a stored query')
    parser.add_argument('params', nargs='*', help='Parameters for the stored query or, if saving, the query itself, with question marks for parameters')

def query(client, request):
    if request.args.save:
        cmd = sql.format_sql_cmd(" ".join(request.args.params))
        with sqlite3.connect(crossbot.db_path) as con:
            query = '''
            INSERT OR REPLACE INTO query_shorthands(name, command, userid, timestamp)
            VALUES(?, ?, ?, ?)
            '''
            con.execute(query, (request.args.name, cmd, request.userid, datetime.now()))
        request.reply("Saved new query `{}` from {}".format(request.args.name, client.user(request.userid)))
    elif request.args.name:
        params = [sql.format_sql_cmd(param) for param in request.args.params]
        with sqlite3.connect(crossbot.db_path) as con:
            query = '''
            SELECT command FROM query_shorthands
            WHERE name = ?
            '''
            result = con.execute(query, (request.args.name,)).fetchone()
        if result:
            cmd, = result
            try:
                with Pool() as pool:
                    print(cmd)
                    result = pool.apply_async(sql.do_sql, [cmd] + params).get(1)
            except TimeoutError:
                result = "you cant dos me even with saved queries, incident reported"

            result = sql.format_sql_result(result, client)
            request.reply(result)
        else:
            request.reply("No known command `{}`".format(request.args.name))
    else:
        with sqlite3.connect(crossbot.db_path) as con:
            queries = con.execute('''
            SELECT name, userid, timestamp, command FROM query_shorthands
            ''').fetchall()

        msgs = []
        for (name, userid, timestamp, command) in queries:
            n_args = command.count('?')
            if n_args:
                maybe_s = '' if n_args == 1 else 's'
                args = ' (takes {} arg{})'.format(n_args, maybe_s)
            else:
                args = ''
            msg = '*{}* by {}{}:\n {}'.format(name, client.user(userid), args, command)
            msgs.append(msg)

        if msgs:
            request.reply('\n\n'.join(msgs))
        else:
            request.reply('There are no saved messages yet... make one with `query --save ...`!')
