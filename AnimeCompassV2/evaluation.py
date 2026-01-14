#-----------------------------
#----Codigo extra no usado ---
#-----------------------------
def evaluate_anime(test_anime_name, k=5):
    target_row = kg.df[kg.df['Name'] == test_anime_name]
    if target_row.empty:
        return None
    
    target_genres = set(target_row.iloc[0]['Genres'])
    recommendations = kg.search_top_k(test_anime_name, k=k)
    
    hits = 0
    first_hit_rank = None
    transr_scores = []

    for i, rec in enumerate(recommendations):
        if rec['name'] == test_anime_name:
            continue

        rec_genres = set(genres_dict.get(rec['name'], [])) 
        
        intersection = target_genres.intersection(rec_genres)
        if len(intersection) > 0: 
            hits += 1
            if first_hit_rank is None:
                first_hit_rank = i + 1 
        
        transr_scores.append(rec['transr'])

    actual_k = len(recommendations)
    precision = hits / actual_k if actual_k > 0 else 0
    reciprocal_rank = 1 / first_hit_rank if first_hit_rank else 0
    avg_graph_proximity = np.mean(transr_scores) if transr_scores else 0

    return {
        "precision": round(precision, 3),
        "mrr": round(reciprocal_rank, 3),
        "proximity": round(avg_graph_proximity, 4),
        "hits": hits
    }