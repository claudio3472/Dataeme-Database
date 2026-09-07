from geopy.geocoders import Nominatim
import re

def autofill_portugal_address(zip_code: str):
    """
    Looks up a Portuguese NNNN-NNN postal code and extracts 
    the components needed to autofill a form.
    """
    # Clean and validate format (NNNN-NNN or NNNNNNN)
    clean_zip = re.sub(r'\D', '', zip_code)
    if len(clean_zip) != 7:
        return {"error": "Invalid Portuguese zip code format. Must be 7 digits (e.g., 1250-096)."}
    
    formatted_zip = f"{clean_zip[:4]}-{clean_zip[4:]}"
    
    # Initialize OpenStreetMap Nominatim Geocoder
    # Make sure to use a unique user_agent string per OSM policy
    geolocator = Nominatim(user_agent="pt_address_autofill_agent")
    
    try:
        # Search specifically within Portugal (country_codes='pt') for better speed and accuracy
        location = geolocator.geocode(formatted_zip, addressdetails=True, country_codes='pt')
        
        if not location or 'address' not in location.raw:
            return {"error": f"No address details found for zip code {formatted_zip}."}
        
        address_data = location.raw['address']
        
        # Safely parse structural elements with fallback values
        autofill_form = {
            "street": address_data.get('road', address_data.get('suburb', '')),
            "city": address_data.get('city', address_data.get('town', address_data.get('village', ''))),
            "municipality": address_data.get('municipality', ''),
            "district_region": address_data.get('state', address_data.get('county', '')),
            "country": address_data.get('country', 'Portugal'),
            "postal_code": formatted_zip
        }
        
        return autofill_form

    except Exception as e:
        return {"error": f"An API connection error occurred: {str(e)}"}


zip_input = "2700-329"
form_data = autofill_portugal_address(zip_input)

print(f"Results for {zip_input}:")
for field, value in form_data.items():
    print(f"  {field.capitalize()}: {value}")
