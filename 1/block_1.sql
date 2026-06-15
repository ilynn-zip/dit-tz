-- Задача 1 Выбери самый прослушиваемый Rock-альбом
select
	a.title as 'album'
	,ar.name as 'artist'
	,count(*) as 'listens'
from
	listening_logs ll
join songs s on 
	ll.song_id = s.song_id
join albums a on
	s.album_id = a.album_id
join artists ar on
	a.artist_id = ar.artist_id
join song_genres sg on
	ll.song_id = sg.song_id
where
	sg.genre_id = (
	select
		genre_id
	from
		genres g
	where
		name = 'Rock')
group by
	a.album_id
	,ar.artist_id
order by
	listens desc
limit 1;


-- Задача 2 Кто в топ-20% по хитам
with top_songs as( 
select
	ll.song_id
	,count(ll.user_id) as 'listens'
from
	listening_logs ll
group by
	ll.song_id
order by listens desc),
top20 as(
select
	song_id
from
	top_songs
limit (
select
	ceil(count(*) * 0.2)
from
	top_songs))
select
	a.name as 'artist'
	,count(t.song_id) as 'top_songs'
from
	top20 t
join song_artists sa on
	t.song_id = sa.song_id
join artists a on
	sa.artist_id = a.artist_id
group by
	artist
order by
	top_songs desc
limit 1;


-- Задача 3 Альбом с самой крутой коллаборацией
with collab as (
select
	s.album_id
	,s.song_id
from
	songs s
join song_artists sa on
	s.song_id = sa.song_id
group by
	sa.song_id
having
	count(sa.artist_id) > 1)
select
	a.title as 'album'
	,ar.name as 'artist'
	,count(c.song_id) as 'collab_count'
from
	collab c
join albums a on
	c.album_id = a.album_id
join artists ar on
	a.artist_id = ar.artist_id
group by
	a.album_id
order by
	collab_count desc
limit 1;


-- Задача 4 Динамика прослушивания по месяцам
select
	strftime('%Y-%m', ll.listen_time) as 'year_month'
	,count(*) as 'total_listens'
from
	listening_logs ll
group by
	year_month
order by
	year_month;


-- Задача 5 Популярность жанров по регионам
select 
	g.name as 'genre'
	,ll.region 
	,count(ll.song_id) as 'total_listens'
from
	listening_logs ll
join song_genres sg on
	ll.song_id = sg.song_id
join genres g on
	sg.genre_id = g.genre_id
group by
	g.genre_id
	,ll.region
order by 
	g.name
	,ll.region;


	
