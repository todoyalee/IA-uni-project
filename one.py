from flask import Flask,render_template,request,redirect, url_for


app=Flask(__name__)

formData={}

@app.route("/",methods=['POST','GET'])
def home():

    if request.method=='POST':
        lastname=request.form['lname']
        firstname=request.form['fname']

        formData['lastname']=lastname
        formData['firstname']=firstname

        return redirect(url_for('output'))
    

@app.route('/output')
def output():
    return render_template('output.html',name=formData['firstname'])
    

if __name__ =="__main__":
    app.run(debug=True)