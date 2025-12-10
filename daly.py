import mysql.connector

mysql=mysql.connector.connect(

    host="localhost",
    user="root",
    passwd="",
    database="mightguy",
)

mycursor=mysql.cursor()
#now i'm gonna create a table   
mycursor.execute("CREATE TABLE QUESTIONS ( id INT AUTO_INCREMENT PRIMARY KEY, question VARCHAR(200) )") 
#mycursor.execute("insert into QUESTIONS(id ,question) values(%s,%s)" ,(19,"shira"))
mysql.commit()

#val=("question")
#mycursor.execute(sql,val)
#mysql.commit() ; 
#print("data is saved")