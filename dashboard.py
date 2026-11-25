import io
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Vendite e redditività", page_icon="📊", layout="wide")
REQUIRED = ['Order Date','Ship Date','Category','Sub-Category','Sales','Profit','Region','State','Quantity']
STATES = {'California':(36.78,-119.42),'New York':(43,-75),'Texas':(31,-99),'Florida':(28,-82),'Washington':(47.4,-120.7),'Illinois':(40,-89),'Lombardia':(45.6,9.9),'Lazio':(41.9,12.5),'Piemonte':(45.1,7.8),'Veneto':(45.6,11.8),'Toscana':(43.4,11),'Sicilia':(37.6,14)}

def demo():
    rng = np.random.default_rng(42)
    n=1500
    categories={'Furniture':['Chairs','Tables','Bookcases'],'Office Supplies':['Paper','Binders','Storage'],'Technology':['Phones','Accessories','Machines']}
    cat=rng.choice(list(categories),n)
    dates=pd.Timestamp('2023-01-01')+pd.to_timedelta(rng.integers(0,1096,n),unit='D')
    sales=np.round(rng.gamma(2,120,n),2)
    states=rng.choice(list(STATES)[:6],n)
    regions={'California':'West','Washington':'West','New York':'East','Texas':'Central','Illinois':'Central','Florida':'South'}
    return pd.DataFrame({'Order Date':dates,'Ship Date':dates+pd.to_timedelta(rng.integers(1,8,n),unit='D'),'Category':cat,'Sub-Category':[rng.choice(categories[c]) for c in cat],'Sales':sales,'Profit':np.round(sales*rng.uniform(-.2,.4,n),2),'Region':[regions[s] for s in states],'State':states,'Quantity':rng.integers(1,10,n)})

def clean(raw, dayfirst):
    df=raw.copy()
    df.columns=df.columns.str.strip()
    if df.columns.duplicated().any():
        raise ValueError('Il file contiene nomi di colonne duplicati.')
    missing=set(REQUIRED)-set(df.columns)
    if missing: raise ValueError('Colonne mancanti: '+', '.join(sorted(missing)))
    before_null=df[REQUIRED].isna().sum()
    duplicates=int(df.duplicated().sum())
    df=df.drop_duplicates().copy()
    for c in ['Order Date','Ship Date']:
        df[c]=pd.to_datetime(df[c],errors='coerce',dayfirst=dayfirst)
    for c in ['Sales','Profit','Quantity']:
        df[c]=pd.to_numeric(df[c],errors='coerce')
    for c in ['Category','Sub-Category','Region','State']:
        df[c]=df[c].astype('string').str.strip().replace('',pd.NA)
    issues=df[REQUIRED].isna().sum()
    invalid=df[REQUIRED].isna().any(axis=1) | (df['Quantity']<0) | (df['Ship Date']<df['Order Date'])
    invalid |= ~np.isfinite(df[['Sales','Profit','Quantity']]).all(axis=1)
    rejected=df.loc[invalid].copy()
    df=df.loc[~invalid].copy()
    df['Year']=df['Order Date'].dt.year
    return df, before_null, issues, duplicates, rejected

st.title('Vendite e redditività')
st.caption('Analisi degli ordini • importi in euro • filtri condivisi tra tutti i grafici')
with st.sidebar:
    st.header('Dati e filtri')
    upload=st.file_uploader('Carica CSV o Excel',type=['csv','xlsx'])
    dayfirst=st.checkbox('Date nel formato giorno/mese/anno',value=True)
    sep=st.selectbox('Separatore CSV',[',',';','\t'])
    st.caption('I numeri devono usare il punto decimale, senza simboli di valuta o separatori delle migliaia.')
try:
    raw=(pd.read_excel(upload) if upload.name.endswith('.xlsx') else pd.read_csv(upload,sep=sep)) if upload else demo()
    df, nulls, issues, duplicates, rejected=clean(raw,dayfirst)
except Exception as e:
    st.error(str(e)); st.stop()
if not upload: st.info('Dati dimostrativi sintetici: carica il tuo dataset per analizzare le vendite reali.')
with st.expander('Qualità e pulizia dei dati'):
    st.write(f'Righe originali: {len(raw):,} · Duplicati esatti rimossi: {duplicates:,} · Righe escluse per dati mancanti, non validi, quantità negative o spedizione precedente all’ordine: {len(rejected):,} · Righe utilizzabili: {len(df):,}')
    st.caption('I duplicati vengono rimossi confrontando tutte le colonne. Vendite e utili negativi sono mantenuti. Senza un identificativo ordine, righe identiche potrebbero rappresentare transazioni distinte.')
    st.dataframe(pd.DataFrame({'Nulli originali':nulls,'Nulli dopo conversione':issues}))
    if len(rejected): st.download_button('Scarica righe escluse',rejected.to_csv(index=False).encode('utf-8-sig'),'righe_escluse.csv')
if df.empty: st.warning('Nessuna riga valida disponibile.'); st.stop()
with st.sidebar:
    years=st.multiselect('Anno',sorted(df.Year.unique()),default=sorted(df.Year.unique()))
    cats=st.multiselect('Categoria',sorted(df.Category.unique()),default=sorted(df.Category.unique()))
    regions=st.multiselect('Area geografica',sorted(df.Region.unique()),default=sorted(df.Region.unique()))
    metric=st.radio('Classifica sottocategorie per',['Vendite (€)','Quantità'])
f=df[df.Year.isin(years)&df.Category.isin(cats)&df.Region.isin(regions)]
if f.empty: st.warning('Nessun dato per i filtri selezionati.'); st.stop()
sales=f.Sales.sum(); profit=f.Profit.sum()
for col,label,value in zip(st.columns(4),['Vendite','Utile','Margine sul fatturato','Quantità'],[f'€ {sales:,.2f}',f'€ {profit:,.2f}',f'{profit/sales:.1%}' if sales else 'N/D',f'{f.Quantity.sum():,.0f}']): col.metric(label,value)
a=f.groupby('Year',as_index=False)[['Sales','Profit']].sum()
st.subheader('Vendite e utili per anno')
st.plotly_chart(px.bar(a,x='Year',y=['Sales','Profit'],barmode='group',labels={'value':'Euro','variable':'Misura','Year':'Anno'},color_discrete_sequence=['#2563eb','#14b8a6']),use_container_width=True)
st.dataframe(a.rename(columns={'Year':'Anno','Sales':'Vendite (€)','Profit':'Utile (€)'}),hide_index=True)
left,right=st.columns(2)
with left:
    st.subheader('Top 5 sottocategorie')
    m='Sales' if metric=='Vendite (€)' else 'Quantity'
    top=f.groupby('Sub-Category',as_index=False)[m].sum().nlargest(5,m).sort_values(m)
    st.plotly_chart(px.bar(top,x=m,y='Sub-Category',orientation='h',labels={m:metric,'Sub-Category':'Sottocategoria'}),use_container_width=True)
with right:
    st.subheader('Redditività per categoria')
    c=f.groupby('Category',as_index=False)[['Sales','Profit']].sum()
    st.plotly_chart(px.bar(c,x='Category',y='Profit',labels={'Category':'Categoria','Profit':'Utile (€)'}),use_container_width=True)
st.subheader('Mappa interattiva delle vendite')
st.caption('I punti rappresentano il centro indicativo di ogni Stato/regione, non gli indirizzi degli ordini. Sono riconosciuti alcuni Stati USA e regioni italiane; per altre località carica anche Latitude e Longitude numeriche.')
if {'Latitude','Longitude'}.issubset(f.columns):
    mapped=f.assign(Latitude=pd.to_numeric(f.Latitude,errors='coerce'),Longitude=pd.to_numeric(f.Longitude,errors='coerce'))
else:
    mapped=f.copy()
    mapped['Latitude']=mapped.State.map(lambda s: STATES.get(s,(None,None))[0])
    mapped['Longitude']=mapped.State.map(lambda s: STATES.get(s,(None,None))[1])
valid=mapped.Latitude.between(-90,90)&mapped.Longitude.between(-180,180)
if (~valid).any(): st.warning(f'{(~valid).sum()} righe senza coordinate valide escluse solo dalla mappa. Località: '+', '.join(mapped.loc[~valid,'State'].unique()))
g=mapped.loc[valid].groupby(['State','Latitude','Longitude'],as_index=False)[['Sales','Profit']].sum()
if len(g):
    g['Dimensione']=g.Sales.abs()
    st.plotly_chart(px.scatter_mapbox(g,lat='Latitude',lon='Longitude',size='Dimensione',color='Sales',hover_name='State',hover_data={'Sales':':.2f','Profit':':.2f','Dimensione':False},mapbox_style='carto-positron',zoom=2,height=480,size_max=45,color_continuous_scale='Blues'),use_container_width=True)
    st.caption('Dimensione dei punti: valore assoluto delle vendite nette. Le tessere della mappa richiedono una connessione Internet.')
else: st.info('Aggiungi Latitude e Longitude al file per visualizzare queste località.')
with st.expander('Dati filtrati'):
    st.dataframe(f,hide_index=True)
st.download_button('Scarica dati puliti e filtrati',f.to_csv(index=False).encode('utf-8-sig'),'vendite_pulite.csv','text/csv')
