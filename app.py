from flask import Flask, render_template, request, jsonify
from scraper import scrape_business_data
from dataclasses import asdict

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.get_json()

    # Validate input
    search_for = data.get('search_for')
    total = data.get('total')

    if not isinstance(search_for, str) or not search_for.strip():
        return jsonify({"error": "search_for must be a non-empty string"}), 400

    if not isinstance(total, int) or total <= 0:
        return jsonify({"error": "total must be a positive integer"}), 400

    # Call the scraper function
    try:
        business_list = scrape_business_data(search_for, total)
        
        # Convert the business_list object to JSON-compatible format
        business_data = [asdict(business) for business in business_list.business_list]
        
        return jsonify({"businesses": business_data}), 200
    except Exception as e:
        app.logger.error(f"Error during scraping: {e}")
        return jsonify({"error": "An error occurred during scraping", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
