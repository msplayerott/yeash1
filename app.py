import requests
import json
import os
import random
import re
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

EMBY_CONFIG = {
    "server": "https://play.roarzone.net",
    "username": "roarzone_guest",
    "password": "",
    "deviceId": "1e58531d-f79d-420e-8d1f-275900e30433"
}

def clean_title(name):
    name = re.sub(r'^\d+[\.\s]+', '', name)
    tags = [
        'Complete', 'converted', 'reencoded', 'w1080', '1080p', '720p', 
        'WEB-DL', 'HDRip', 'BluRay', 'x264', 'x265', 'HEVC', r'S\d+', 'Bengali', 'w720'
    ]
    for tag in tags:
        name = re.sub(rf'\b{tag}\b', '', name, flags=re.IGNORECASE)
    name = name.replace('.', ' ').replace('_', ' ')
    return re.sub(r'\s+', ' ', name).strip()

def fetch_emby_series(parent_id, category_name, save_filename):
    folder_name = "wak_fu"
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        
    print(f"Mandamina Emby Series: {category_name} (ID: {parent_id}) -> Folder: {folder_name}")
    
    session = requests.Session()
    
    auth_url = f"{EMBY_CONFIG['server']}/emby/Users/AuthenticateByName"
    auth_header = f'MediaBrowser Client="Python Script", Device="GitHub Action", DeviceId="{EMBY_CONFIG["deviceId"]}", Version="1.0.0"'
    payload = {"Username": EMBY_CONFIG['username'], "Pw": EMBY_CONFIG['password']}
    headers = {"Content-Type": "application/json", "X-Emby-Authorization": auth_header}
    
    try:
        auth_res = session.post(auth_url, json=payload, headers=headers, timeout=15, verify=False)
        auth_data = auth_res.json()
        
        if "AccessToken" in auth_data:
            token = auth_data["AccessToken"]
            user_id = auth_data["SessionInfo"]["UserId"]
            
            params = {
                "ParentId": parent_id,
                "Recursive": "true",
                "IncludeItemTypes": "Series",
                "Fields": "PrimaryImageTag,ProductionYear,Overview,CommunityRating,Genres,RunTimeTicks,OfficialRating",
                "api_key": token
            }
            
            items_url = f"{EMBY_CONFIG['server']}/emby/Users/{user_id}/Items"
            series_res = session.get(items_url, params=params, timeout=20, verify=False)
            series_data = series_res.json()
            
            if "Items" in series_data:
                final_items = []
                for series in series_data["Items"]:
                    series_id = series["Id"]
                    raw_series_name = series["Name"]
                    clean_name = clean_title(raw_series_name)
                    year = series.get("ProductionYear", "")
                    
                    display_title = f"{clean_name} ({year})" if year else clean_name
                    print(f" - Maka Series: {display_title}")
                    
                    seasons = []
                    seasons_url = f"{EMBY_CONFIG['server']}/emby/Shows/{series_id}/Seasons"
                    s_params = {"UserId": user_id, "api_key": token}
                    s_res = session.get(seasons_url, params=s_params, timeout=15, verify=False)
                    s_data = s_res.json()
                    
                    if "Items" in s_data:
                        for season in s_data["Items"]:
                            season_id = season["Id"]
                            
                            episodes_url = f"{EMBY_CONFIG['server']}/emby/Shows/{series_id}/Episodes"
                            e_params = {
                                "SeasonId": season_id,
                                "UserId": user_id,
                                "Fields": "PrimaryImageTag,Overview,RunTimeTicks",
                                "api_key": token
                            }
                            e_res = session.get(episodes_url, params=e_params, timeout=20, verify=False)
                            e_data = e_res.json()
                            
                            episodes = []
                            if "Items" in e_data:
                                for episode in e_data["Items"]:
                                    raw_ep_name = episode["Name"]
                                    clean_ep_title = clean_title(raw_ep_name)
                                    idx = episode.get("IndexNumber", 1)
                                    
                                    runtime_ticks = episode.get("RunTimeTicks", 0)
                                    runtime_minutes = round(runtime_ticks / 600000000)
                                    
                                    ep_obj = {
                                        "downStatus": "off",
                                        "downUrl": f"{EMBY_CONFIG['server']}/emby/Videos/{episode['Id']}/stream?static=true&api_key={token}",
                                        "duration": f"{runtime_minutes}m",
                                        "episode_title": f"E{idx} ∙ {clean_ep_title}",
                                        "headers": {
                                            "Referer": "https://play.roarzone.info/",
                                            "Origin": "",
                                            "User-Agent": ""
                                        },
                                        "posterUrl": f"{EMBY_CONFIG['server']}/emby/Items/{episode['Id']}/Images/Primary?api_key={token}",
                                        "streamUrl": f"{EMBY_CONFIG['server']}/emby/Videos/{episode['Id']}/stream?static=true&api_key={token}",
                                        "view": 0
                                    }
                                    episodes.append(ep_obj)
                            
                            season_title = season.get("Name", "").lower()
                            seasons.append({
                                "episodes": episodes,
                                "season_title": season_title
                            })
                    
                    raw_rating = series.get("CommunityRating", 0.0)
                    imdb_rating = round(float(raw_rating), 1)
                    if imdb_rating > 0:
                        imdb_votes = int(imdb_rating * 15234) + random.randint(500, 2000)
                    else:
                        imdb_votes = 0
                        
                    series_obj = {
                        "category": category_name,
                        "director": "N/A",
                        "genre": series.get("Genres", []),
                        "imdbRating": imdb_rating,
                        "imdbVotes": imdb_votes,
                        "language": "Hindi",
                        "posterUrl": f"{EMBY_CONFIG['server']}/emby/Items/{series_id}/Images/Primary?quality=90&api_key={token}",
                        "premium": False,
                        "quality": "HD",
                        "releaseDate": str(year) if year else "N/A",
                        "resolution": "1080p",
                        "seasons": seasons,
                        "sliderStatus": "off",
                        "sliderUrl": "",
                        "status": "on",
                        "storyline": series.get("Overview", ""),
                        "title": display_title,
                        "triler": ""
                    }
                    final_items.append(series_obj)
                    
                db_path = os.path.join(folder_name, save_filename)
                with open(db_path, "w", encoding="utf-8") as f:
                    json.dump(final_items, f, indent=2, ensure_ascii=False)
                    
                print(f"Fahombiazana: Series voatahiry ao amin'ny {db_path}")
        else:
            print(f"Tsy nahomby ny fidirana ho an'ny {category_name}")
    except Exception as e:
        print(f"Hadisoana ho an'ny {category_name}: {e}")

if __name__ == "__main__":
    fetch_emby_series("89535", "Bengali", "series_bengali.json")
