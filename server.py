import socket, threading, json, time

HOST="0.0.0.0"
PORT=7777
ADMIN_NAME="Andrey"
ADMIN_PASSWORD="admin123"

players={}
lock=threading.Lock()

def send(sock, data):
    sock.sendall((json.dumps(data, ensure_ascii=False)+"\n").encode())

def broadcast(data):
    raw=(json.dumps(data, ensure_ascii=False)+"\n").encode()
    with lock:
        for p in list(players.values()):
            try: p["sock"].sendall(raw)
            except: pass

def admin_only(name):
    with lock:
        return bool(players.get(name,{}).get("admin"))

def command(name, cmd, sock):
    if not admin_only(name):
        send(sock, {"type":"error","message":"Недостаточно прав"})
        return

    parts=cmd.split()
    if not parts:
        return

    c=parts[0].lower()

    if c=="/players":
        with lock:
            data=[{"name":n,"admin":p["admin"],"money":p["money"],"level":p["level"]}
                  for n,p in players.items()]
        send(sock, {"type":"players","players":data})

    elif c=="/money" and len(parts)>=3:
        target=parts[1]
        try: amount=int(parts[2])
        except: return
        with lock:
            if target in players:
                players[target]["money"] += amount
                target_sock=players[target]["sock"]
                newmoney=players[target]["money"]
            else: target_sock=None
        if target_sock:
            send(target_sock, {"type":"stats","money":newmoney})
            send(sock, {"type":"system","message":f"Выдано ${amount} игроку {target}"})

    elif c=="/level" and len(parts)>=3:
        target=parts[1]
        try: level=int(parts[2])
        except: return
        with lock:
            if target in players:
                players[target]["level"]=max(1,level)
                target_sock=players[target]["sock"]
            else: target_sock=None
        if target_sock:
            send(target_sock, {"type":"stats","level":level})
            send(sock, {"type":"system","message":f"Уровень {target}: {level}"})

    elif c=="/tp" and len(parts)>=2:
        target=parts[1]
        with lock:
            exists=target in players
            ts=players[target]["sock"] if exists else None
        if ts:
            send(ts, {"type":"teleport","x":0,"y":0,"z":0})
            send(sock, {"type":"system","message":f"Телепортирован {target} на spawn"})

    elif c=="/spawn" and len(parts)>=2:
        target=parts[1]
        with lock:
            ts=players[target]["sock"] if target in players else None
        if ts: send(ts, {"type":"spawn"})

    elif c=="/mute" and len(parts)>=2:
        target=parts[1]
        with lock:
            if target in players:
                players[target]["muted"]=True
                ts=players[target]["sock"]
            else: ts=None
        if ts: send(ts, {"type":"system","message":"Чат отключён администратором"})

    elif c=="/kick" and len(parts)>=2:
        target=parts[1]
        with lock: p=players.get(target)
        if p:
            send(p["sock"], {"type":"kicked","message":"Вы были отключены администратором"})
            try: p["sock"].close()
            except: pass
            send(sock, {"type":"system","message":f"{target} отключён"})

    elif c=="/say":
        text=" ".join(parts[1:])
        broadcast({"type":"admin","message":text})

    else:
        send(sock, {"type":"system","message":"Команды: /players /money /level /tp /spawn /mute /kick /say"})

def client(sock, addr):
    name=None
    try:
        f=sock.makefile("r", encoding="utf-8")
        send(sock, {"type":"hello","message":"BR Test v2 server"})
        for line in f:
            try: msg=json.loads(line)
            except: continue
            typ=msg.get("type")

            if typ=="login":
                requested=str(msg.get("name","Player"))[:24].strip() or "Player"
                password=str(msg.get("password",""))
                admin=requested==ADMIN_NAME and password==ADMIN_PASSWORD

                with lock:
                    if requested in players:
                        send(sock, {"type":"error","message":"Этот ник уже используется"})
                        continue
                    players[requested]={
                        "sock":sock,"admin":admin,"money":5000,"level":1,
                        "muted":False,"joined":time.time()
                    }
                name=requested
                send(sock, {"type":"login_ok","name":name,"admin":admin,
                            "money":5000,"level":1})
                broadcast({"type":"system","message":f"{name} подключился"})
                continue

            if not name: continue

            if typ=="chat":
                text=str(msg.get("message",""))[:200]
                with lock: muted=players.get(name,{}).get("muted",False)
                if not muted:
                    broadcast({"type":"chat","name":name,"message":text})

            elif typ=="command":
                command(name, str(msg.get("command","")), sock)

    except Exception:
        pass
    finally:
        if name:
            with lock: players.pop(name,None)
            broadcast({"type":"system","message":f"{name} вышел"})
        try: sock.close()
        except: pass

server=socket.socket()
server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
server.bind((HOST,PORT))
server.listen()
print(f"BR Test v2 server started on {HOST}:{PORT}")
print(f"ADMIN: {ADMIN_NAME} / {ADMIN_PASSWORD}")

while True:
    sock,addr=server.accept()
    threading.Thread(target=client,args=(sock,addr),daemon=True).start()
