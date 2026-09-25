package com.example.brtest;

import android.app.*;
import android.os.*;
import android.view.*;
import android.widget.*;
import java.io.*;
import java.net.*;
import org.json.*;

public class MainActivity extends Activity {
 EditText name,password,host,command;
 TextView status;
 Button admin,send;
 Socket socket;
 BufferedReader in;
 BufferedWriter out;

 public void onCreate(Bundle b){
  super.onCreate(b);
  setContentView(R.layout.activity_main);

  name=findViewById(R.id.name);
  password=findViewById(R.id.password);
  host=findViewById(R.id.host);
  command=findViewById(R.id.command);
  status=findViewById(R.id.status);
  admin=findViewById(R.id.admin);
  send=findViewById(R.id.send);

  findViewById(R.id.connect).setOnClickListener(v->connect());
  admin.setOnClickListener(v->{
   command.setVisibility(View.VISIBLE);
   send.setVisibility(View.VISIBLE);
   status.setText("Админ-панель открыта");
  });
  send.setOnClickListener(v->sendCommand());
 }

 void connect(){
  final String n=name.getText().toString().trim();
  final String h=host.getText().toString().trim();
  final String p=password.getText().toString();

  if(n.isEmpty()){status.setText("Введите ник"); return;}

  status.setText("Подключение...");
  new Thread(()->{
   try{
    socket=new Socket(h,7777);
    in=new BufferedReader(new InputStreamReader(socket.getInputStream()));
    out=new BufferedWriter(new OutputStreamWriter(socket.getOutputStream()));

    JSONObject login=new JSONObject();
    login.put("type","login");
    login.put("name",n);
    login.put("password",p);
    send(login);

    String line;
    while((line=in.readLine())!=null){
     JSONObject x=new JSONObject(line);
     String type=x.optString("type");

     if(type.equals("login_ok")){
      boolean isAdmin=x.optBoolean("admin");
      runOnUiThread(()->{
       status.setText(isAdmin ? "ВЫ ВОШЛИ КАК АДМИНИСТРАТОР" :
                               "Вы вошли как игрок");
       if(isAdmin) admin.setVisibility(View.VISIBLE);
      });
     } else if(type.equals("system") || type.equals("admin")){
      String m=x.optString("message");
      runOnUiThread(()->status.setText(m));
     } else if(type.equals("chat")){
      String m=x.optString("name")+": "+x.optString("message");
      runOnUiThread(()->status.setText(m));
     } else if(type.equals("players")){
      runOnUiThread(()->status.setText("Игроков онлайн: "+x.optJSONArray("players").length()));
     } else if(type.equals("kicked")){
      runOnUiThread(()->status.setText("Вы отключены администратором"));
      break;
     }
    }
   }catch(Exception e){
    runOnUiThread(()->status.setText("Ошибка: "+e.getMessage()));
   }
  }).start();
 }

 void sendCommand(){
  String c=command.getText().toString().trim();
  if(c.isEmpty()) return;
  try{
   JSONObject j=new JSONObject();
   j.put("type","command");
   j.put("command",c);
   send(j);
   command.setText("");
  }catch(Exception e){status.setText(e.getMessage());}
 }

 void send(JSONObject j)throws Exception{
  out.write(j.toString());
  out.write("\n");
  out.flush();
 }
}