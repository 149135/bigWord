from app.app import app, init_db
import os

if __name__ == '__main__':
    # Ensure directories exist
    if not os.path.exists('app/static/uploads'):
        os.makedirs('app/static/uploads')
        
    # Initialize DB
    init_db()
    
    # Run
    app.run(debug=True, port=5000)



