from flask import Flask, render_template, request, redirect, url_for
import pickle
import numpy as np

# ── Load data ──────────────────────────────────────────────────────────────────
popular_df        = pickle.load(open('popular_df.pkl', 'rb'))
pt                = pickle.load(open('pt.pkl', 'rb'))
books             = pickle.load(open('books.pkl', 'rb'))
similarity_scores = pickle.load(open('similarity_score.pkl', 'rb'))

app = Flask(__name__)
# app.secret_key = 'bookverse2024'

# All book titles for autocomplete
all_titles = sorted(list(pt.index))


# ── Home page – Top 50 books ──────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html',
        book_name=list(popular_df['Book-Title'].values),
        author   =list(popular_df['Book-Author'].values),
        image    =list(popular_df['Image-URL-M'].values),
        votes    =list(popular_df['num_ratings'].values),
        rating   =[round(r, 1) for r in popular_df['avg_ratings'].values],
    )


# ── Recommend page ────────────────────────────────────────────────────────────
@app.route('/recommend')
def recommend_ui():
    return render_template('recommend.html', all_titles=all_titles)


@app.route('/recommend_books', methods=['POST'])
def recommend():
    user_input = request.form.get('user_input', '').strip()
    book_indices = np.where(pt.index == user_input)[0]

    if len(book_indices) == 0:
        partial = [b for b in pt.index if user_input.lower() in b.lower()]
        if len(partial) == 0:
            return render_template('recommend.html',
                error="No book found matching '" + user_input + "'. Please try another title.",search_term=user_input,
                all_titles=all_titles)
        return render_template('recommend.html',
            suggestions=partial[:6], search_term=user_input, all_titles=all_titles)

    index = book_indices[0]
    similar_items = sorted(
        list(enumerate(similarity_scores[index])),
        key=lambda x: x[1], reverse=True
    )[1:9]

    data = []
    for i, _ in similar_items:
        temp = books[books['Book-Title'] == pt.index[i]].drop_duplicates('Book-Title')
        if temp.empty:
            continue
        row = temp.iloc[0]
        data.append({
            'title' : row['Book-Title'],
            'author': row['Book-Author'],
            'image' : row['Image-URL-M'],
            'year'  : str(row['Year-Of-Publication'])
        })

    return render_template('recommend.html',
        data=data, search_term=user_input, all_titles=all_titles)


# ── Book detail ───────────────────────────────────────────────────────────────
@app.route('/book')
def book_detail():
    title = request.args.get('title', '')
    book_row = books[books['Book-Title'] == title].drop_duplicates('Book-Title')
    if book_row.empty:
        return redirect(url_for('index'))

    row = book_row.iloc[0]
    book = {
        'title'    : row['Book-Title'],
        'author'   : row['Book-Author'],
        'image'    : row['Image-URL-M'],
        'year'     : str(row['Year-Of-Publication']),
        'publisher': str(row['Publisher'])
    }

    pop = popular_df[popular_df['Book-Title'] == title]
    avg_rating  = round(float(pop['avg_ratings'].values[0]), 1) if not pop.empty else None
    num_ratings = int(pop['num_ratings'].values[0])             if not pop.empty else None

    similar = []
    if title in pt.index:
        idx  = np.where(pt.index == title)[0][0]
        top4 = sorted(list(enumerate(similarity_scores[idx])), key=lambda x: x[1], reverse=True)[1:5]
        for i, _ in top4:
            t2 = books[books['Book-Title'] == pt.index[i]].drop_duplicates('Book-Title')
            if not t2.empty:
                r2 = t2.iloc[0]
                similar.append({
                    'title' : r2['Book-Title'],
                    'author': r2['Book-Author'],
                    'image' : r2['Image-URL-M']
                })

    return render_template('book_detail.html',
        book=book, avg_rating=avg_rating, num_ratings=num_ratings, similar=similar)


# ── Analytics Dashboard ───────────────────────────────────────────────────────
@app.route('/dashboard')
def dashboard():
    pub_counts = books['Publisher'].value_counts().head(10)
    pub_labels = pub_counts.index.tolist()
    pub_values = pub_counts.values.tolist()

    year_data = {}
    for y in books['Year-Of-Publication'].astype(str):
        if y.isdigit():
            yr = int(y)
            if 1990 <= yr <= 2004:
                year_data[yr] = year_data.get(yr, 0) + 1
    year_labels = sorted(year_data.keys())
    year_values = [year_data[y] for y in year_labels]

    auth_counts = popular_df['Book-Author'].value_counts().head(8)
    auth_labels = auth_counts.index.tolist()
    auth_values = auth_counts.values.tolist()

    buckets = {'1-2':0,'2-3':0,'3-4':0,'4-5':0,'5-6':0,'6-7':0,'7-8':0,'8+':0}
    for val in popular_df['avg_ratings']:
        if   val < 2: buckets['1-2'] += 1
        elif val < 3: buckets['2-3'] += 1
        elif val < 4: buckets['3-4'] += 1
        elif val < 5: buckets['4-5'] += 1
        elif val < 6: buckets['5-6'] += 1
        elif val < 7: buckets['6-7'] += 1
        elif val < 8: buckets['7-8'] += 1
        else:         buckets['8+']  += 1



    stats = {
        'total_books'  : f"{len(books):,}",
        'total_ratings': f"{int(popular_df['num_ratings'].sum()):,}",
        'avg_rating'   : round(float(popular_df['avg_ratings'].mean()), 1)
    }

    return render_template('dashboard.html',
        pub_labels=pub_labels, pub_values=pub_values,
        year_labels=year_labels, year_values=year_values,
        auth_labels=auth_labels, auth_values=auth_values,
        rating_labels=list(buckets.keys()), rating_values=list(buckets.values()), stats=stats)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
