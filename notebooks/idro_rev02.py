

import io
import zipfile
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

import seaborn as sns
from itertools import combinations
from tqdm import tqdm
from scipy.ndimage import gaussian_filter1d

# gestioen anomalia su jupyterlab
if not hasattr(plt.rcParams, "_get"):
    plt.rcParams._get = plt.rcParams.get

#soglie solo per la stazione di Faenza (non più necessarioe)
SOGLIE = {"soglia_0": 3.5, "soglia_1": 4.5, "soglia_2": 6.0} #dummy, poi agiornata
COLORI = {"soglia_0": "#e8a33d", "soglia_1": "#d9622b", "soglia_2": "#c0392b"}
BLU = "#1a5490"



def _leggi_csv(contenuto, nome): #da modificare per la toscana
    """Elettura csv acquisiti da Dext3r"""
    try:
        testo = contenuto.decode("utf-8-sig", errors="replace")
    except Exception:
        return None, f"{nome}: impossibile decodificare"

    righe = testo.replace("\r\n", "\n").split("\n")

    i0 = next((i for i, r in enumerate(righe)
               if r.startswith("Inizio validità")), None)
    if i0 is None:
        return None, f"{nome}: intestazione non trovata"

    i1 = next((i for i in range(i0 + 1, len(righe))
               if righe[i].strip() == ""), len(righe))
    if i1 - i0 < 2:
        return None, f"{nome}: nessuna riga di dati"

    try:
        tab = pd.read_csv(io.StringIO("\n".join(righe[i0:i1])))
    except Exception as e:
        return None, f"{nome}: {type(e).__name__}"

    if tab.shape[1] < 3:
        return None, f"{nome}: attese 3 colonne, trovate {tab.shape[1]}"

    stazione = righe[2].strip() if len(righe) > 2 and righe[2].strip() else "?"

    out = pd.DataFrame({
        "stazione": stazione,
        "timestamp": pd.to_datetime(tab.iloc[:, 0], utc=True, errors="coerce"),
        #"timestamp_fine": pd.to_datetime(tab.iloc[:, 1], utc=True, errors="coerce"),
        "valore": pd.to_numeric(tab.iloc[:, 2], errors="coerce"),
        "file": nome,
    })
    return out, None


def carica(cartella):
    #Legge ricorsivamente tutti zip, che contengono csv, della cartella sorgente
    percorso = Path(cartella)
    if not percorso.exists():
        raise FileNotFoundError(f"cartella non trovata: {percorso.resolve()}")

    pezzi, problemi = [], []

    for f in sorted(percorso.rglob("*")):
        if f.suffix.lower() == ".csv":
            d, err = _leggi_csv(f.read_bytes(), f.name)
            (pezzi if d is not None else problemi).append(d if d is not None else err)
        elif f.suffix.lower() == ".zip":
            try:
                with zipfile.ZipFile(f) as z:
                    for n in z.namelist():
                        if n.lower().endswith(".csv"):
                            d, err = _leggi_csv(z.read(n), f.name)
                            (pezzi if d is not None else problemi).append(
                                d if d is not None else err)
            except zipfile.BadZipFile:
                problemi.append(f"{f.name}: zip non leggibile")

    if not pezzi:
        raise ValueError(f"nessun file valido in {percorso.resolve()}")

    df = pd.concat(pezzi, ignore_index=True)
    scartati = df.timestamp.isna().sum()
    df = df.dropna(subset=["timestamp"]).reset_index(drop=True)

    print(f"file letti      {len(pezzi)}")
    print(f"righe           {len(df):,}")
    print(f"periodo         {df.timestamp.min():%Y-%m-%d} / {df.timestamp.max():%Y-%m-%d}")
    print(f"stazioni        {', '.join(df.stazione.unique())}")
    if scartati:
        print(f"righe scartate  {scartati:,} (timestamp non valido)")
    for p in problemi:
        print(f"  [!] {p}")
    #rimuovi duplicati e tieni dati corretti
    df=df.sort_values(by=['valore','timestamp'], ascending=False).drop_duplicates(subset=['stazione','timestamp'], keep='first').reset_index(drop=True).copy()
    return df.sort_values(by='timestamp', ascending=True).copy().reset_index(drop=True)


def tseq_statsy(
    df,
    sensor):
    #
    SOGLIE_SENSORE= [sensor.soglia_0.values[0], 
         sensor.soglia_1.values[0],
         sensor.soglia_2.values[0]
        ]
    SOGLIE = {"soglia_0": SOGLIE_SENSORE[0], "soglia_1": SOGLIE_SENSORE[1], "soglia_2": SOGLIE_SENSORE[2]}
    #
    print(*SOGLIE.values())
    #
    print(df.stazione.unique())
    #
    df['next_timestamp']=df.timestamp.shift(-1)
    #analisi campionamento
    df['campionamento_min']=(df['next_timestamp'] - df['timestamp'])// pd.Timedelta(minutes=1)
    df['is_same_year'] = (df['next_timestamp'].dt.year == df['timestamp'].dt.year).astype(int)
    #
    df['timestamp_year']=df['next_timestamp'].dt.year
    #
    df_camp = df.query('is_same_year == 1').groupby(['timestamp_year']).agg(
                        lista_minuti=('campionamento_min', lambda x: list(set(x))),
                        n_15=('campionamento_min', lambda x: (x == 15).sum()),
                        n_30=('campionamento_min', lambda x: (x == 30).sum())
                    ).reset_index()
    #
    df_camp['p30']=df_camp.n_30/(df_camp.n_30+df_camp.n_15)
    #
    df_camp['p15']=df_camp.n_15/(df_camp.n_30+df_camp.n_15)
    #
    '''
    y30_s, y30_e= df_camp.query("p30>.99").timestamp_year.min().astype(int), df_camp.query("p30>.99").timestamp_year.max().astype(int)
    y15_s, y15_e= df_camp.query("p15>.99").timestamp_year.min().astype(int), df_camp.query("p15>.99").timestamp_year.max().astype(int)
    #
    df_time_30 = pd.DataFrame(index=pd.date_range(f"{y30_s}-01-01", f"{y30_e}-12-31 23:30", freq="30min",tz="UTC", name='timestamp'))

    df_time_15 = pd.DataFrame(index=pd.date_range(f"{y15_s}-01-01", f"{y15_e}-12-31 23:30", freq="15min",tz="UTC", name='timestamp'))

    last_ts=df.timestamp.max()

    df_time_15 = df_time_15.loc[:last_ts]
    #
    minutes_manage={
        'start_30': df_time_30.index.min() ,
        
        'end_30': df_time_30.index.max(),
        
        'start_15': df_time_15.index.min(), 

        'end_15': df_time_15.index.max()
    }
    '''
    q30 = df_camp.query("p30>.99")
    if not q30.empty:
        y30_s, y30_e = int(q30.timestamp_year.min()), int(q30.timestamp_year.max())
        df_time_30 = pd.DataFrame(index=pd.date_range(f"{y30_s}-01-01", f"{y30_e}-12-31 23:30", freq="30min", tz="UTC", name='timestamp'))
    else:
        df_time_30 = pd.DataFrame(index=pd.DatetimeIndex([], tz="UTC", name='timestamp'))

    # --- Gestione range 15 minuti ---
    q15 = df_camp.query("p15>.99")
    if not q15.empty:
        y15_s, y15_e = int(q15.timestamp_year.min()), int(q15.timestamp_year.max())
        df_time_15 = pd.DataFrame(index=pd.date_range(f"{y15_s}-01-01", f"{y15_e}-12-31 23:30", freq="15min", tz="UTC", name='timestamp'))
        # Taglia i 15 minuti all'ultimo timestamp reale solo se ci sono dati
        df_time_15 = df_time_15.loc[:df.timestamp.max()]
    else:
        df_time_15 = pd.DataFrame(index=pd.DatetimeIndex([], tz="UTC", name='timestamp'))
    #
    #
    minutes_manage = {
        'start_30': df_time_30.index.min(),
        'end_30': df_time_30.index.max(),
        'start_15': df_time_15.index.min(),
        'end_15': df_time_15.index.max()
    }
    #
    df=df.sort_values(['timestamp','valore']).drop_duplicates(subset=['timestamp'], keep='first').reset_index(drop=True).copy()
    #
    df=df[['valore','timestamp']].copy()
    #
    df = df.set_index('timestamp')
    #
    df_timeseq=pd.concat([df_time_30,df_time_15])
    #
    df_merged =df_timeseq.merge(df, how='left', left_index=True, right_index=True)
    #
    # Cerca minuti che non sono multipli di 30, oppure timestamp che hanno secondi diversi da zero
    anomalie = df[(df.index.minute % 15 != 0) | (df.index.second != 0)]
    #
    print(anomalie)
    #
    df_extra = df[~df.index.isin(df_timeseq.index)]
    print(df_extra)
    #
    #
    #modifica dati <0 con 0
    df_merged.loc[df_merged['valore'] < 0, 'valore'] = 0.0
    #df_merged[df_merged.valore<0].valore=0.0
    #
    invalid_data=len(df_merged[(df_merged.valore.isna() )])#|( df_merged.valore <0.0)])
    p_valid=1-(invalid_data/len(df_merged))
    #
    invalid_data_year=df_merged[(df_merged.valore.isna() )].copy()
    #
    #gb_invalid_data_year=invalid_data_year.groupby(invalid_data_year.index.year).size()
    gb_invalid_data_year = (
        invalid_data_year.groupby(invalid_data_year.index.year)
        .size()
        .rename_axis('y_date')
        .reset_index(name='n_d_sample_invalid')
    )
    #
    
    #
    gb_all_df_merged = (
    df_merged.groupby(df_merged.index.year)
    .size()
    .rename_axis('y_date')
    .reset_index(name='n_d_sample')
    )
    #
    df_y_recap=gb_all_df_merged.merge(gb_invalid_data_year, how='left', on=['y_date']).fillna(0).copy()
    #
    df_y_recap['p_valid']=100.0*(1-(df_y_recap.n_d_sample_invalid/df_y_recap.n_d_sample))
    df_y_recap['stazione']=sensor.stazione.iloc[0]
    df_y_recap['n_stazione']=sensor.n_stazione.astype(int).iloc[0]
    #
    return [df_y_recap.copy(),df_merged.copy(),SOGLIE , minutes_manage]

def over_s_analysis(df_sen=None,
                    SOGLIE=None,
                   sensor=None):
    df_sen['soglia_1']=SOGLIE['soglia_1']
    df_sen['soglia_2']=SOGLIE['soglia_2']
    #
    df_sen['in_s_analysis'] = df_sen.assign(valore=df_sen['valore'].fillna(-1)).apply(
        lambda x: 1 if x['valore'] > x['soglia_1'] and x['valore'] <= x['soglia_2'] 
        else (2 if x['valore'] > x['soglia_2'] else 0), 
        axis=1
    )
    #df_sen.index.tz_convert('Europe/Rome')
    idx_italy_date = df_sen.index.tz_convert('Europe/Rome').date #gestion e con day su italia per no creare prlbkemi dopo.
    day_max = (
    df_sen.groupby([idx_italy_date, df_sen.in_s_analysis])
        .size()
        .rename_axis(['d_date', 'in_s_analysis'])
        .reset_index(name='n_d_sample')
    )
    #
    df_over2=day_max[day_max.in_s_analysis==2].query("n_d_sample>2") #soglia di sicurezza 2 acuiqizioni sopra soglia 2
    #
    df_b1a2=day_max[day_max.in_s_analysis==1].query("n_d_sample>2") #soglia 2 acquziioni in betwen soglia 1-2
    #
    df_sover_local=pd.concat([df_over2.copy(),
                          df_b1a2.copy()
                         ]).reset_index(drop=True)
    #
    df_sover_local['stazione']=sensor.stazione.iloc[0]
    df_sover_local['n_stazione']=sensor.n_stazione.astype(int).iloc[0]
    #
    return df_sover_local.copy()
    
#
def data_prep(
    data_raw=None,
    soglie=None,
    df_stats_over=None,
    shift_ts=None,
    sensor=None ):
    #shift_ts=df_raw_data[3]
    #data_raw=df_raw_data[1].copy()
    #df_raw_data[2]['soglia_0']
    data_raw['soglia_1']=soglie['soglia_1']
    data_raw['soglia_2']=soglie['soglia_2']
    #
    data_raw.loc[data_raw['valore'].isna(), 'val_valore_raw'] = int(-1) #valore orifinale non valido
    #
    data_raw.loc[(~data_raw['valore'].isna() | data_raw['valore']<0.0), 'val_valore_raw'] =int( 0 )#valore origiale negativo
    #
    data_raw.loc[(~data_raw['valore'].isna() | data_raw['valore']>=0.0),  'val_valore_raw'] = int(1) #valore originale >0
    #
    data_raw.loc[data_raw.val_valore_raw == -1, 'value_use'] = np.nan
    data_raw.loc[data_raw.val_valore_raw == 0, 'value_use'] = 0
    data_raw.loc[data_raw.val_valore_raw == 1, 'value_use'] = data_raw['valore']
    #
    data_raw.loc[
        (data_raw.index >= shift_ts['start_30']) & (data_raw.index <= shift_ts['end_30']), 
        'step_ts'
        ] = 30

    data_raw.loc[
        (data_raw.index >= shift_ts['start_15']) & (data_raw.index <= shift_ts['end_15']), 
        'step_ts'
        ] = 15
    
    data_raw_ts_ko=data_raw[ data_raw.step_ts.isna()].copy()
    
    print('KO ts in raw data:\n')
    print(len(data_raw_ts_ko))
    #
    #
    day_o2=df_stats_over.query('in_s_analysis==2').reset_index(drop=True)
    #
    day_o1b2=df_stats_over.query('in_s_analysis==1').reset_index(drop=True)
    #
    #
    data_raw['d_date'] = data_raw.index.tz_convert('Europe/Rome').normalize().tz_localize(None)
    #
    day_o2['d_date'] = pd.to_datetime(day_o2['d_date']).dt.normalize().dt.tz_localize(None)
    #join per avere info su giorno con valori tra 1 e 2
    day_o1b2['d_date'] = pd.to_datetime(day_o1b2['d_date']).dt.normalize().dt.tz_localize(None)
    #
    data_raw = (
        data_raw.reset_index() # keep index
        .merge(day_o2[['d_date', 'in_s_analysis']], on='d_date', how='left')
        .rename(columns={'in_s_analysis': 'over_s2'})
        .merge(day_o1b2[['d_date', 'in_s_analysis']], on='d_date', how='left')
        .rename(columns={'in_s_analysis': 'b_s1as2','timestamp':'timestamp_utc' })
        .set_index('timestamp_utc') #index timestamp again
    )
    
    data_raw = data_raw.fillna({
        'over_s2': 0, 
        'b_s1as2': 0
    })
    #
    data_raw['over_s2'] = data_raw['over_s2'].replace(2, 1)
    #
    
    data_raw_ts_ko.head()
    #
    #preprocesing data
    data_raw['xt']= data_raw.value_use/data_raw.soglia_2 #normlized wrt soglia2
    #
    data_raw['log_1pxt']= np.log(1+data_raw['xt']) #lg preprocess
    #
    sensor.rename(columns={'stat_end_corso[0: monte, n:valle]':'stat_end_corso'}, inplace=True)
    #
    column_sensor = [
    'bacino', 
    'corso',
    'stat_end_corso',
    'n_stazione',
    'stazione',
    'quota_sensore_mslm',
    'lat',
    'lon'
    ]
    #
    for col in column_sensor:
        data_raw[col] = sensor[col].iloc[0]
    #
    #data_raw.columns
    col_ordered=['bacino', 
                 'corso',
                 'stat_end_corso',
                 'n_stazione',
                 'stazione', 
                 'quota_sensore_mslm', 
                 'lat', 'lon',
                 'd_date',
                 'step_ts',
                 'over_s2',
                 'b_s1as2',                 
                 'valore', 
                 'soglia_1', 'soglia_2', 
                 'val_valore_raw', #validazione valore raw 1 buono 0 o -1 non utili oer statistiche, -1 da non usare per previsioni (o cumune ha dato nan
                 'value_use',
                 'xt', 
                 'log_1pxt'
                ]
    data_raw=data_raw[col_ordered].copy()
    return data_raw
#
# da rivedere




def grafico_stazione(df_big, nome_stazione, limiti_y=None, figsize=(11, 3.4)):
    BLU = "#1a5490"
    COL_S1 = "#d9622b" 
    COL_S2 = "#c0392b" 
    # Filtra la big table per stazione e ordina temporalmente usando l'indice
    s = df_big.query("stazione == @nome_stazione").sort_index().copy()
    
    if s.empty:
        print(f"Stazione '{nome_stazione}' non trovata.")
        return None
        
    fig, ax = plt.subplots(figsize=figsize)
    
    # Plotta usando l'indice (timestamp_utc) e la colonna valore
    ax.plot(s.index, s.valore, lw=0.4, color=BLU, zorder=2)
    
    # Estrae le soglie dinamiche
    s1 = s.soglia_1.iloc[0]
    s2 = s.soglia_2.iloc[0]
    ax.axhline(s1, color=COL_S1, linestyle="--", lw=1.2, zorder=3, label=f"S1 ({s1}m)")
    ax.axhline(s2, color=COL_S2, linestyle="-", lw=1.5, zorder=3, label=f"S2 ({s2}m)")
    
    # Evidenzia i giorni con allerte s2 (versione corretta)
    giorni_s2 = s[s.over_s2 == 1].index.normalize().unique()
    for g in giorni_s2:
        ax.axvspan(g, g + pd.Timedelta(days=1), color=COL_S2, alpha=0.5, zorder=1, lw=0)
        
    if limiti_y is not None:
        ax.set_ylim(*limiti_y)
        fuori = int(((s.valore < limiti_y[0]) | (s.valore > limiti_y[1])).sum())
        if fuori:
            ax.annotate(f"{fuori} valori fuori scala",
                        xy=(0.005, 0.04), xycoords="axes fraction",
                        fontsize=7.5, color="#888")
    
    ax.set_ylabel("livello (m)")
    ax.set_title(f"{nome_stazione} - livello idrometrico, {s.index.min():%Y}-{s.index.max():%Y}",
                 loc="left", fontsize=11)
                 
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.margins(x=0.01)
    ax.grid(alpha=0.25, lw=0.5)
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    
    return fig







# ---------------------------------------------------------------------
# statistiche giorni sopra soglia
# ---------------------------------------------------------------------
def stats_giorni_sopra(
    df_big=None,
    df_stats_over=None,
    livello=2):
    #livello: 2 = sopra soglia_2 (rossa), 1 = tra soglia_1 e soglia_2
    gby_over = (
        df_stats_over[df_stats_over.in_s_analysis == livello]
        .groupby('stazione')
        .size()
        .reset_index(name='n_day_over')
    )
    #
    gby_all = (
        df_big[['stazione', 'd_date']].drop_duplicates()
        .groupby('stazione')
        .size()
        .reset_index(name='all_day')
    )
    #
    stats = gby_all.merge(gby_over, how='left', on='stazione').fillna({'n_day_over': 0})
    stats['p_day_over'] = 100.0 * stats.n_day_over / stats.all_day
    #
    return stats.sort_values('n_day_over', ascending=False).reset_index(drop=True)


def stazioni_per_giorno(
    df_stats_over=None,
    livello=2):
    #per ogni giorno: quante e quali stazioni sono sopra soglia
    df = df_stats_over[df_stats_over.in_s_analysis == livello]
    #
    per_giorno = (
        df.groupby('d_date')
        .agg(n_stazioni=('stazione', 'nunique'),
             stazioni=('stazione', lambda s: sorted(s.unique())))
        .sort_values('n_stazioni', ascending=False)
    )
    return per_giorno


# ---------------------------------------------------------------------
# grafici
# ---------------------------------------------------------------------
def grafico_stazione(
    df=None,
    stazione=None,
    col='value_use'):
    #serie temporale della stazione con soglia_1 e soglia_2
    g = df[df.stazione == stazione]
    #
    fig, ax = plt.subplots(figsize=(11, 3.4))
    ax.plot(g.index, g[col], lw=.6, color='steelblue')
    ax.axhline(g.soglia_1.iloc[0], color='orange', ls='--', lw=1, label='soglia_1')
    ax.axhline(g.soglia_2.iloc[0], color='red', ls='--', lw=1, label='soglia_2')
    ax.set(title=stazione, ylabel=f'{col} [m]')
    ax.legend(loc='upper left', fontsize=8)
    plt.tight_layout()
    return fig


def distribuzione_globale(
    df=None,
    col='xt',
    xlim=(-.5, 1),
    ylim=(0, 3 * 10**5)):
    #istogramma (con kde) e cumulativa di col su tutte le stazioni insieme
    x = df[col].dropna().to_numpy(dtype=np.float32) #float32 per memoria
    #
    fig, ax = plt.subplots(1, 2, figsize=(12, 4))
    sns.histplot(x, kde=True, ax=ax[0])
    ax[0].set(xlim=xlim, ylim=ylim, xlabel=col, title=f'istogramma {col}')
    sns.ecdfplot(x, ax=ax[1])
    ax[1].set(xlim=xlim, xlabel=col, title=f'cumulativa {col}')
    plt.tight_layout()
    return fig


def ecdf_per_stazione(
    df=None,
    col='xt',
    xlim=(0, 1)):
    #cumulativa di col, una curva per stazione
    x = df[[col, 'stazione']].dropna()
    #
    g = sns.displot(data=x, x=col, hue='stazione', kind='ecdf')
    g.ax.set_xlim(*xlim)
    return g


def densita_per_stazione(
    df=None,
    col='xt',
    n_bin=2000,
    sigma=5,
    xlim=(0, 1),
    ylim=(0, 30)):
    #densita' per stazione: istogramma fine + smoothing gaussiano (piu' leggero di kde su milioni di punti)
    x = df[['stazione', col]].dropna()
    #
    lo, hi = np.percentile(x[col], [0.01, 99.99])
    edges = np.linspace(lo, hi, n_bin + 1)
    centers = (edges[:-1] + edges[1:]) / 2
    width = edges[1] - edges[0]
    #
    fig, ax = plt.subplots(figsize=(12, 6))
    for staz, g in x.groupby('stazione'):
        counts, _ = np.histogram(g[col].to_numpy(), bins=edges)
        dens = gaussian_filter1d(counts.astype(float), sigma=sigma)
        dens /= dens.sum() * width
        ax.plot(centers, dens, lw=1, label=staz)
    #
    ax.legend(fontsize=7, ncol=3)
    ax.set(xlim=xlim, ylim=ylim, xlabel=col, ylabel='densita')
    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------
# cross-correlazione tra stazioni
# ---------------------------------------------------------------------
def cross_corr_stazioni(
    df=None,
    col='xt',
    passo=15,
    max_ore=48,
    min_n=4 * 24 * 30):
    #per ogni coppia (a, b) provo i ritardi in [-max_ore, +max_ore] e tengo quello con corr massima
    #ritardo > 0: b anticipa a (confronto a[t] con b[t - ritardo])
    M = (df.pivot_table(index=df.index, columns='stazione', values=col)
           .resample(f'{passo}min').mean())
    #
    lags = range(-max_ore * 60 // passo, max_ore * 60 // passo + 1)
    n = len(M)
    risultati = []
    #
    for a, b in tqdm(list(combinations(M.columns, 2))):
        xa = M[a].to_numpy()
        xb = M[b].to_numpy()
        migliore = None
        #
        for l in lags:
            if l >= 0:
                u, v = xa[l:], xb[:n - l]
            else:
                u, v = xa[:n + l], xb[-l:]
            #
            ok = ~np.isnan(u) & ~np.isnan(v)
            if ok.sum() < min_n:
                continue #pochi dati in comune
            #
            u, v = u[ok], v[ok]
            if u.std() == 0 or v.std() == 0:
                continue #serie costante: corr non definita
            #
            r = np.corrcoef(u, v)[0, 1]
            if migliore is None or r > migliore['corr']:
                migliore = {'st1': a, 'st2': b, 'corr': r,
                            'ritardo_min': l * passo, 'n_punti': int(ok.sum())}
        #
        if migliore is not None:
            risultati.append(migliore)
    #
    return pd.DataFrame(risultati).sort_values('corr', ascending=False).reset_index(drop=True)


def matrice_corr(coppie=None):
    #da tabella coppie a matrice quadrata simmetrica
    stazioni = sorted(set(coppie.st1) | set(coppie.st2))
    C = (coppie.pivot(index='st1', columns='st2', values='corr')
               .reindex(index=stazioni, columns=stazioni))
    C = C.combine_first(C.T)
    for s in stazioni:
        C.loc[s, s] = 1.0
    return C


def heatmap_corr(
    C=None,
    file_png=None):
    #ordino le stazioni secondo il primo autovettore (quanto seguono l'andamento comune)
    Cf = C.fillna(0)
    valori, vettori = np.linalg.eigh(Cf.values)
    ordine = np.argsort(vettori[:, -1])
    Co = Cf.iloc[ordine, ordine]
    #
    fig = plt.figure(figsize=(11, 10))
    sns.heatmap(Co, cmap='RdBu_r', vmin=-1, vmax=1, xticklabels=True, yticklabels=True)
    if file_png is not None:
        plt.savefig(file_png, dpi=200, bbox_inches='tight')
    return fig


# ---------------------------------------------------------------------
# contesto valido prima del superamento soglia
# ---------------------------------------------------------------------
def contesto_prima_soglia(
    df=None,
    soglia='soglia_2',
    min_campioni=3,
    max_passo='30min'):
    #per ogni stazione-giorno (d_date, giorno italiano) con almeno min_campioni sopra soglia
    #(stesso criterio di over_s_analysis: n_d_sample > 2) prendo il primo timestamp sopra soglia
    #e conto quante misure valide consecutive ci sono prima, fermandomi al primo NaN
    #o a un salto nella griglia piu' lungo di max_passo
    risultati = []
    #
    for stazione, g in df.groupby('stazione'):
        g = g.sort_index()
        valido = g['value_use'].notna()
        salto = g.index.to_series().diff() > pd.Timedelta(max_passo)
        #
        blocco = (~valido | salto).cumsum()
        consecutivi = valido.groupby(blocco).cumsum()
        prima = consecutivi.shift(1, fill_value=0).where(~salto, 0).astype(int) #misure valide prima di t (t escluso)
        #
        sopra = g[g['value_use'] > g[soglia]]
        n_sopra = sopra.groupby('d_date').size()
        giorni_ok = n_sopra[n_sopra >= min_campioni].index
        primi = sopra[sopra.d_date.isin(giorni_ok)].groupby('d_date').head(1)
        if primi.empty:
            continue
        #
        pos = g.index.get_indexer(primi.index)
        n = prima.iloc[pos].to_numpy()
        inizio = g.index[pos - n]
        #
        risultati.append(pd.DataFrame({
            'stazione': stazione,
            'd_date': primi.d_date.to_numpy(),
            'primo_superamento': primi.index,
            'step_ts': primi.step_ts.to_numpy(),
            'n_validi_prima': n,
            'inizio_contesto': inizio.where(n > 0),
            'ore_contesto': (primi.index - inizio).total_seconds() / 3600,
        }))
    #
    return pd.concat(risultati, ignore_index=True)


def confronto_giorni(
    df_stats_over=None,
    contesto=None,
    livello=2):
    #controllo: i giorni del contesto devono coincidere con quelli di over_s_analysis
    giorni_over = (
        df_stats_over[df_stats_over.in_s_analysis == livello]
        .groupby('stazione')['d_date'].nunique()
        .rename('giorni_over_s_analysis')
    )
    giorni_contesto = contesto.groupby('stazione').size().rename('giorni_contesto')
    #
    confronto = pd.concat([giorni_over, giorni_contesto], axis=1).fillna(0).astype(int)
    confronto['differenza'] = confronto.giorni_contesto - confronto.giorni_over_s_analysis
    return confronto


def riepilogo_contesto(
    contesto=None,
    ore=(1, 3, 6, 12, 24)):
    #step = numero di misure, ore = durata effettiva (differenza di timestamp)
    riepilogo = (
        contesto.groupby('stazione')
        .agg(giorni=('n_validi_prima', 'size'),
             senza_contesto=('n_validi_prima', lambda s: (s == 0).sum()),
             q25_step=('n_validi_prima', lambda s: s.quantile(.25)),
             mediana_step=('n_validi_prima', 'median'),
             q75_step=('n_validi_prima', lambda s: s.quantile(.75)),
             mediana_ore=('ore_contesto', 'median'))
    )
    #
    for h in ore:
        riepilogo[f'pct_almeno_{h}h'] = contesto.groupby('stazione')['ore_contesto'].apply(lambda s: 100 * s.ge(h).mean())
    #
    return riepilogo.round(1)


def boxplot_contesto(
    contesto=None,
    col='n_validi_prima',
    xlim=None,
    xlabel='Step validi consecutivi prima del primo rosso giornaliero'):
    ordine = contesto.groupby('stazione')[col].median().sort_values().index
    #
    fig, ax = plt.subplots(figsize=(12, 9))
    sns.boxplot(data=contesto, x=col, y='stazione', order=ordine, showfliers=False, ax=ax)
    sns.stripplot(data=contesto, x=col, y='stazione', order=ordine,
                  color='black', alpha=0.4, size=3, ax=ax)
    ax.set(xlabel=xlabel, ylabel='Stazione', title='Contesto disponibile prima del superamento')
    if xlim is not None:
        ax.set_xlim(*xlim)
    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------
# aree di copertura per richiesta SAR
# ---------------------------------------------------------------------
def aree_copertura(
    per_giorno=None,
    df_anag=None,
    min_stazioni=5,
    margine_km=1):
    #per ogni giorno con piu' di min_stazioni sopra rossa: rettangolo e quadrato che contengono le stazioni
    #+ una riga TUTTE_LE_DATE con l'unione delle stazioni coinvolte
    import geopandas as gpd
    from shapely.geometry import box
    #
    giorni = per_giorno[per_giorno.n_stazioni > min_stazioni].sort_index()
    #
    selezione = (
        giorni[['stazioni']].explode('stazioni')
        .reset_index()
        .rename(columns={'stazioni': 'stazione'})
    )
    selezione['data'] = pd.to_datetime(selezione.d_date).dt.strftime('%Y-%m-%d')
    #
    anag = df_anag[['stazione', 'bacino', 'corso', 'lat', 'lon']].copy()
    anag[['lat', 'lon']] = anag[['lat', 'lon']].apply(pd.to_numeric, errors='coerce')
    #
    punti = selezione.merge(anag, on='stazione', how='left', validate='many_to_one')
    senza_coordinate = punti[punti.lat.isna() | punti.lon.isna()][['data', 'stazione']]
    print('stazioni senza coordinate:\n', senza_coordinate)
    punti = punti.dropna(subset=['lat', 'lon'])
    #
    geo = gpd.GeoDataFrame(punti, geometry=gpd.points_from_xy(punti.lon, punti.lat), crs='EPSG:4326')
    geo_m = geo.to_crs(geo.estimate_utm_crs()) #UTM per avere metri
    #
    margine_m = margine_km * 1000
    gruppi = list(geo_m.groupby('data')) + [('TUTTE_LE_DATE', geo_m)]
    risultati, geometrie = [], []
    #
    for data, g in gruppi:
        xmin, ymin, xmax, ymax = g.total_bounds
        xmin, ymin, xmax, ymax = xmin - margine_m, ymin - margine_m, xmax + margine_m, ymax + margine_m
        #
        larghezza, altezza = xmax - xmin, ymax - ymin
        lato = max(larghezza, altezza)
        cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
        #
        rettangolo = box(xmin, ymin, xmax, ymax)
        quadrato = box(cx - lato / 2, cy - lato / 2, cx + lato / 2, cy + lato / 2)
        #
        risultati.append({
            'data': data,
            'n_stazioni_localizzate': g.stazione.nunique(),
            'corsi': ', '.join(sorted(g.corso.dropna().unique())),
            'larghezza_km': larghezza / 1000,
            'altezza_km': altezza / 1000,
            'rettangolo_km2': rettangolo.area / 1e6,
            'lato_quadrato_km': lato / 1000,
            'quadrato_km2': quadrato.area / 1e6,
        })
        geometrie += [{'data': data, 'tipo': 'rettangolo', 'geometry': rettangolo},
                      {'data': data, 'tipo': 'quadrato', 'geometry': quadrato}]
    #
    aree = pd.DataFrame(risultati)
    coperture = gpd.GeoDataFrame(geometrie, crs=geo_m.crs)
    return geo, aree, coperture


def mappa_copertura(
    geo=None,
    aree=None,
    coperture=None,
    carto_key=None,
    data='TUTTE_LE_DATE',
    margine_km=1):
    #data = 'YYYY-MM-DD' oppure 'TUTTE_LE_DATE'
    import folium
    #
    if data == 'TUTTE_LE_DATE':
        punti = geo.drop_duplicates('stazione')
    else:
        punti = geo[geo.data == data]
    punti = punti[['stazione', 'bacino', 'corso', 'geometry']].to_crs('EPSG:4326')
    #
    cop = coperture[coperture.data == data].to_crs('EPSG:4326')
    info = aree[aree.data == data].iloc[0]
    #
    m = folium.Map(tiles=None)
    folium.TileLayer(
        tiles='https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png?key=' + carto_key.strip(),
        attr='© OpenStreetMap contributors © CARTO',
        subdomains='abcd',
        name='CARTO Voyager',
        max_zoom=20,
    ).add_to(m)
    #
    punti.explore(m=m, column='corso', tooltip=['stazione', 'bacino', 'corso'],
                  marker_kwds={'radius': 6}, name='Stazioni sopra rossa')
    #
    for tipo, colore in [('rettangolo', 'blue'), ('quadrato', 'red')]:
        folium.GeoJson(
            cop[cop.tipo == tipo].geometry.__geo_interface__,
            style_function=lambda f, c=colore: {'color': c, 'weight': 2, 'fillOpacity': 0.05},
            name=tipo,
        ).add_to(m)
    #
    etichetta = (
        f"<b>{data}</b><br>"
        f"{info.n_stazioni_localizzate} stazioni localizzate<br>"
        f"Rettangolo (blu): {info.larghezza_km:.1f} x {info.altezza_km:.1f} km = {info.rettangolo_km2:.0f} km²<br>"
        f"Quadrato (rosso): {info.lato_quadrato_km:.1f} x {info.lato_quadrato_km:.1f} km = {info.quadrato_km2:.0f} km²<br>"
        f"Margine: {margine_km} km"
    )
    m.get_root().html.add_child(folium.Element(
        '<div style="position:fixed;top:15px;left:60px;z-index:9999;background:white;'
        'padding:10px;border:2px solid red;border-radius:5px;font-size:12px;">' + etichetta + '</div>'
    ))
    #
    xmin, ymin, xmax, ymax = cop.total_bounds
    m.fit_bounds([[ymin, xmin], [ymax, xmax]])
    folium.LayerControl().add_to(m)
    return m
