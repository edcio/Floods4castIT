#Allertamento calibrato in due fasi per alluvioni in Italia (inizio da Emilia-Romagna e poi valutazione Toscana)

🚧 **REPO IN COSTRUZIONE** 🚧
Proposta progettuale in fase di impostazione e valutaizione. Nessun modello è ancora implementato:
Documentazione flusso logico proposto in valutazione.
Il primo contenuto eseguibile è l'esempio esplorativo sui dati della Fase 1 in notebooks/01_processing_eda_fase1.ipynb

---

## Obiettivo

**Quando** un fiume supererà la soglia di criticità ufficiale (Fase 1, dati a terra da idrometri e frequenza acquisizioni 15 minuti) e 
**quanto il territorio è pronto** a trasformare quella piena in "danno" (Fase 2, solo dati satellirati se frequenza acquisizioni in giorni): 
due potenziali moduli indipendenti che si incontrano solo in una matrice di escalation dell'allerta.

---

## Flusso logico complessivo

```
 SCALA VELOCE — minuti/ore                      SCALA LENTA — giorni
 (reti di monitoraggio a terra)                 (solo dati satellitari)

 ┌─────────────────────┐                       ┌──────────────────┐
 │ livelli             │                       │ acquisizioni     │
 │ idrometrici         │                       │ Dati             │
 │ da stazioni a terra │                       │ Satellitari      │
 └──────┬──────────────┘                       └────────┬─────────┘
        ▼                                               ▼
 ┌──────────────┐                               ┌──────────────────┐
 │ modello      │                               │ computer vision: │
 │ multi-       │                               │ stato del terreno│
 │ orizzonte    │                               │                  │
 └──────┬───────┘                               └────────┬─────────┘
        ▼                                                ▼
 ┌───────────────────────┐                      ┌──────────────────┐
 │ Uncertainty           │ incertezza applicata │ indice di        │
 │ Quantificazion        │ DOPO il modello      │ PREDISPOSIZIONE  │
 │ (Conformal Prediction)│                      │ per zona         │
 └──────┬────────────────┘                      └────────┬─────────┘
        ▼                                                │
 ┌──────────────────────────┐                            │
 │ P(superamento soglia)    │                            │
 │ + finestra temporale     │                            │
 └────────────┬─────────────┘                            │
              │                                          │
              └────────────────┬─────────────────────────┘
                               ▼
                ┌─────────────────────────────┐
                │   MATRICE DI ESCALATION     │
                │         (bozza)             │
                │            fase 1 →         │
                │  fase 2   niente s1-2 s2-3  │
                │  ↓ alta   att.  ALL. MAX    │
                │    media  ord.  all. ALL.   │
                │    bassa  —     ord. att.   │
                └─────────────────────────────┘
                               ▼
                    allerta finale per zona
```

I due moduli **non si scambiano informazione durante il calcolo**: si incontrano solo nella matrice definitiva. 
Ogni modulo è a se stante.

---

## Fase 1 — previsione del superamento di soglia

```
Dext3r (ER) / SIR (Toscana)  →  features (da definire)  →  Modello/i (da definire)
                                                          │
                                                   UQ (Conformal)
                                                          │
                                              traiettoria + intervallo
                                                          │
                                    derivazioni: P(soglia), finestra [t1,t2]
```

- **Target:** regressione multi-orizzonte del livello ( es: 30 min - 6 h); superamento e tempo al superamento.
- **Soglie:** quelle amministrative ufficiali del livello idrometrico per sezione (codici colore).
- **UQ:** è un livello indipendente dall'architettura dei modelli; il problema che affronta è la quantificazione dell'incertezza.
- **Confronti:** lineari, LightGBM, LSTM, KAN (con potenziale valultazioni di interpretabilità), etc..  ( da valutare)
- 
## Fase 2 — predisposizione del territorio (solo satellite)

```
dati satellitari ──────┐
                       ├──► stack temporale per zona ──► CV, tre livelli (da valutare):
dati satellitari ──────┘                              L1 change detection (baseline)
                                                      L2 segmentazione 
                                                      L3 previsione: stato a t+k giorni
                                                            │
                                              indice di predisposizione
                                              per zona di allerta
                                              (+ UQ, a valle )
```

- **Concetto:** valutazione di "predisposizione al rischio" del suolo in luogo dei metodi "classici" idrologici ma con **osservazioni dei dati satellitari**
- **L'inerzia temporale diversa è il principio di progetto:** il satellite non insegue la piena, descrive lo sfondo su cui la piena arriva.

---

## Struttura del repository (in fase di costruzione)

```
notebooks/
docs/
data/
```


## Roadmap

- [x] Impostazione e rassegna preliminare
- [x] **Verifiche bloccanti:** granularità archivi storici
- [x] `notebooks/01_processing_eda_fase1.ipynb`: scarico e visualizzazione livelli vs soglie (in corso)
- [ ] Fase 1: modelli
- [ ] Fase 1: UQ
- [ ] Fase 2: Dati
- [ ] Fase 2: modelli+UQ
- [ ] Matrice di escalation e validazione sugli eventi (es per il 2023)

________________________________________________________________________________________________________________________________________


# Confronti e valutazioni:

## **1) Nearing et al. (2024) [Google Flood Hub]**
**Global prediction of extreme floods in ungauged watersheds.**

https://www.nature.com/articles/s41586-024-07145-1

LSTM encoder–decoder su 5.680 idrometri, **passo giornaliero** (non minuti o ore), orizzonte 7 giorni, senza alcun dato
osservato di portata in ingresso. La valutazione è per eventi, su soglie definite da tempo di
ritorno, e il risultato principale è che a 5 giorni di anticipo l'affidabilità paragonabile al nowcast di
GloFAS.

È il regime diverso da quello del progetto proposto. A seguire alciuni punti sostanziali:

- il passo è **giornaliero**, non a minuti o ore: la dinamica dei bacini che rispondono in poche ore
  è filtrata via per costruzione;
- la variabile prevista è la **portata**, mentre le **soglie** di criticità italiane
  sono definite sul **livello idrometrico** ufficiali;
- le soglie sembrano derivare da **tempi di ritorno ricalcolati sulla serie simulata di ciascun modello e su valori osservati**
  non valori assoluti pubblicati come nella proposta progettuale dove si fa riferimento a livelli idrometrici ufficiali.
- il modello produce una **distribuzione predittiva** a ogni passo ed i risultati riportano solo
  la mediana 
- sul territorio italiano la copertura è **marginale** e concentrata pochi punti d'interesse (dettaglio nelle immagini).
 
 

**Nel lavoro proposto:** un modulo veloce su livelli idrometrici con inerzie di
15/30 minuti e/o ore proprie del regime strumentato; a valle, una caratterizzazione della predisposizione
del suolo da acquisizioni satellitari che modula l'allerta anziché entrare come forzante a monte. 
Non unicamente previsione da satellite, ma combinazione del dato a terra, che porta la granularità temporale, con
quello satellitare, che porta lo stato del territorio. 
In aggiunta: quantificazione dell'incertezza e confronto sistematico tra modelli alternativi.


### Copertura di Flood Hub sul territorio italiano
(Nota importante, dati ad oggi)

Il portale dichiara oggi una copertura globale dell'ordine di 150 paesi e oltre 240.000 località.
La copertura non è però uniforme in qualità: Google distingue le località **verificate**, dove è
stata possibile una valutazione della qualità del modello contro osservazioni storiche o immagini
satellitari, dalle altre e le prime sono circa 5.000. **Copertura non implica validazione.**

Ad oggi, la copertura in Italia risulta bassa.

Le immagini seguenti documentano la situazione osservata sul territorio italiano ad agosto 2026.

<!-- Immagine 1: vista d'insieme del territorio nazionale -->
![Copertura Flood Hub — Italia, vista d'insieme](docs/img/floodhub-italia-insieme.png)

*Fig. A — Copertura Flood Hub sul territorio nazionale, fonte
[g.co/floodhub](https://g.co/floodhub).*
____________________________________________________________________________________________________________________________________
<!-- Immagine 2: dettaglio sull'area di interesse del progetto -->
![Copertura Flood Hub — dettaglio per le zone coperte (parzialmente/scarsamente) in Italia](docs/img/floodhub-italia-dettaglio.png)

*Fig. B — Dettaglio sull'area di interesse del progetto (EmiliaRomagna - Toscana].* ,fonte
[g.co/floodhub](https://g.co/floodhub).*
____________________________________________________________________________________________________________________________________
<!-- Immagine 3: confronto con paesi con alta copertura (es. India) -->
![Copertura Flood Hub — dettaglio area di studio](docs/img/floodhub-confronto-paesi.png)

*Fig. C — Confronto con paesi con alta copertura (es. India), fonte
[g.co/floodhub](https://g.co/floodhub).*
____________________________________________________________________________________________________________________________________
<!-- Immagine 4: focus italia anche per GloFAS  -->
![Copertura Flood Hub — dettaglio area di studio](docs/img/floodhub-confronto-GloFAS.png)

*Fig. D — Confronto anch su copertura da GIoFAS* , fonte
[GloFAS](https://global-flood.emergency.copernicus.eu/map)

____________________________________________________________________________________________________________________________________

**Nota sulla natura di questa verifica.** La copertura di Flood Hub cambia nel tempo e le immagini fanno riferimento a quanto disponibile ad agosto 2026.
Il posizionamento del progetto **non dipende da questa verifica** rimane un modo diverso e potenzialmente valutabile per allarmi di natura alluvionale con particolare focus sull'Italia e sui bacini che sono sempre più importanti per territori e gestori di infrastrutture per avere sistemi nuovi e che sfruttino dati e informazioni sempre più nuovi ed aggiornati.


____________________________________________________________________________________________________________________________________
____________________________________________________________________________________________________________________________________
____________________________________________________________________________________________________________________________________

## 2 **Roudbari et al. (2024)**

**From data to action in flood forecasting leveraging graph neural networks and digital twin visualization.**

https://www.nature.com/articles/s41598-024-68857-y

Lo studio propone un duplice framework: un modello previsionale e uno strumento di visualizzazione.
Sul lato previsionale una GNN, con architettura encoder–decoder basata su blocchi GCRN (Graph
Convolution Recurrent Network) con approccio **graph learning**: la matrice di
connettività fra le stazioni non è imposta a priori dalla topologia fluviale ma **appresa dai dati**,
scelta motivata dal fatto che la struttura reale della rete può essere ignota o mutare nel tempo.

La variabile prevista è il **livello idrometrico**, a **passo giornaliero**, con orizzonti di 3, 6 e
9 **giorni**, su 8 stazioni nell'area di Terrebonne (Montreal) con serie 2000–2021 da
Environment and Climate Change Canada.

Nel modello predittivo non sono utilizzati dati di precipitazione: gli input sono i
soli livelli delle 8 stazioni. Suddivisione temporale 70/10/20. La valutazione usa MAE, MAPE e RMSE,
confrontando con la media storica e con quattro modelli di previsione spaziotemporale (Informer,
GTS, DCGCN, STAWnet) sviluppati in altri contesti, in particolare per la previsione del traffico.

Sul lato visualizzazione, gli autori costruiscono un gemello digitale della città in ambiente di
game engine per ulteriori simulazioni (fuori contesto rispetto alla proposta progettuale)

A seguire alciuni punti sostanziali rispetto alla proposta progettuale:

- Regime temporale: passo giornaliero e orizzonti di 3–9 giorni: è la scala della
   pianificazione, non quella dell'allertamento su bacini a risposta rapida. La proposta
   progettuale lavora a inerzie di 15/30 minuti e ore, dove l'orizzonte utile si misura in ore.

- Trattamento delle anomalie: i valori mancanti sono ricostruiti con la media storica e la
   serie è poi sottoposta a **smoothing gaussiano**, descritto dagli autori come mezzo per attenuare
   le fluttuazioni improvvise senza compromettere i pattern sottostanti. Su un problema di previsione
   di piene, tuttavia, la fluttuazione improvvisa **è** il segnale di interesse. Nella proposta
   progettuale il filtraggio è limitato al rumore strumentale documentato e verificato sugli eventi,
   e gli eventi maggiori sono oggetto di validazione dedicata anziché di attenuazione. Una parte
   sostanziale del lavoro della proposta progettuale dovrà esser dedicata proprio al preprocessing e alla data quality: definizione
   delle regole e delle metodologie per il trattamento dei dati mancanti e delle misure provenienti
   da strumentazione con potenziali malfunzionamenti.

- Oggetto della valutazione: le metriche riportate sono MAE, MAPE e RMSE aggregate sull'intera
   serie di test, senza alcun riferimento a soglie. Nella proposta progettuale anche il **superamento
   della soglia di criticità ufficiale è oggetto della valutazione**, insieme al tempo di anticipo
   effettivamente disponibile.

- Baseline di confronto: i termini di paragone sono la media storica e quattro modelli nati per
   la previsione del traffico.
Nella proposta progettuale, oltre a vari modelli da comparare, aggiungendo eventualmente GNN, tra i benckmark di prevederebbe anche una valutazione vs un modello semplificato che analizza unicamente una singola stazione di rilevamento.

- Quantificazione dell'incertezza: è assente, il modello produce una previsione puntuale e la
   valutazione è deterministica. La proposta progettuale introduce una verifica della copertura,
   indipendente dal modello predittivo e quindi applicabile anche ad architetture alternative.

- accoppiamento fra previsione e rappresentazione a valle: nel lavoro di riferimento le due
   componenti restano in larga parte separate, e il confronto con la mappa di allagamento del 2017 è
   **qualitativo**, senza metriche di sovrapposizione. Nella proposta progettuale il legame fra
   componente previsiva e componente territoriale è quantificato, ed è centrale: le due parti
   convergono nell'output finale del sistema.

- Informazione territoriale nella previsione: gli autori indicano fra i lavori futuri
   l'integrazione dell'informazione sulla quota del terreno all'interno della rete previsiva,
   osservando che si tratta di un fattore influente attualmente non considerato. La proposta
   progettuale muove in quella direzione, ma con una caratterizzazione dello **stato dinamico** del
   territorio da acquisizioni satellitari.

**Elementi da valutare per integrarli eventualmente nella proposta progettuale.** L'impiego di una GNN è un elemento da considerare nella proposta
progettuale, insieme alla metodologia di gestione del dato. In particolare, la relazione fra le
stazioni di misura appresa dai dati anziché derivata da una mappatura statica basata su informazioni
anagrafiche della rete è un'opzione da valutare in termini di rapporto costi/benefici.




____________________________________________________________________________________________________________________________________
____________________________________________________________________________________________________________________________________
____________________________________________________________________________________________________________________________________

## 3) **Nevo et al. (2022)** [Google- sistema operativo India/Bangladesh]
**Flood forecasting with machine learning models in an operational framework.**

https://hess.copernicus.org/articles/26/4013/2022/
*(N.d.R. il paper precede di due anni Nearing et al. 2024)*

Studioa e allertamento in due parti, Stage forecast model e inundation model. A seguire focus sulla parte di Stage forecast model che è quello d'interesse da valutare.

La previsione è affidata a una rete LSTM. La variabile
prevista è il **livello idrometrico**. Passo orario, orizzonte 8–48 h, 167 idrometri su bacini da
350 a 1.500.000 km² in India e Bangladesh. Fra gli input, oltre ai livelli osservati alla
sezione obiettivo e a monte, anche la precipitazione stimata da dati satellitari.

L'incertezza è modellata direttamente dalla rete con una CMAL (Countable Mixture of Asymmetric
Laplacians): a ogni passo il modello produce i parametri di una insieme di distribuzioni anziché un
singolo valore, viene poi mostrata la fascia fra il 20° e l'80° percentile. L'allarme
scatta quando il massimo del livello previsto sull'intera finestra supera la soglia di allerta
predefinita per quella sezione, fornita dalle autorità nazionali. La valutazione è riportata in
termini di NSE (Nash–Sutcliffe Efficiency) e la vairante Persistent-NSE non con metriche le metriche per valutazione se superamento intercettato o no


A seguire alciuni punti sostanziali rispetto alla proposta progettuale:

- Regime dei bacini: lo studio è progettato per fiumi grandi a risposta lenta,
   e gli autori indicano l'estensione ai bacini sotto i 1.000 km² come sviluppo futuro. Le metriche
   riportate crescono infatti con l'area del bacino. La proposta progettuale lavora su bacini più
   ridotti (caso italiano), a inerzie di 15/30 minuti e/o ore.

- Oggetto della valutazione: lo studio fa parla di un sistema di riferimento che decide in modo binario (allarme o non allarme) rispetto a una soglia, ma viene valutato con NSE e Persistent-NSE. Nella proposta progettuale il **superamento della soglia di criticità è
   l'oggetto stesso della valutazione**, insieme al tempo di anticipo effettivamente disponibile;
   altre metriche saranno definite in base alle valutazioni preliminari.

- Verifica dell'incertezza: la distribuzione predittiva è prodotta e usata, ma la valutazione
   riportata resta su metriche di errore. La proposta progettuale introduce una **verifica della
   copertura**: controllare che la frequenza con cui i valori osservati cadono dentro l'intervallo
   previsto corrisponda al livello dichiarato, e che ciò valga anche separatamente in piena e non
   solo in aggregato. La verifica è indipendente dal modello predittivo, quindi applicabile a
   qualsiasi altro modello, e il livello di confidenza è impostabile in funzione dell'uso.

- Comportamento oltre il record storico: quando l'ampiezza dell'incertezza stimata supera una
   soglia, fissata a 50 cm nel paper, il sistema di riferimento accorcia il lead time fino a
   rientrare sotto quel valore. Nella proposta progettuale la selezione dell'orizzonte è ricondotta
   a un criterio di **copertura verificata** anziché di ampiezza.

- Orizzonte come grandezza derivata: il lead time massimo è, nel paper, un parametro di
   configurazione definito a priori per ciascuna stazione. Su bacini a risposta rapida l'orizzonte
   determina l'utilità stessa del sistema: nella proposta progettuale viene **derivato** dal tempo
   di risposta del bacino e dal punto oltre il quale la copertura non è più verificata.

- Contesto di valutazione: gli autori segnalano in più punti la scarsità di studi di
   valutazione di sistemi operativi e, nel confronto con la letteratura, reperiscono un solo
   termine di paragone (51 idrometri in Iowa) riconoscendone la limitata comparabilità. Non
   risultano riferimenti operativi in area europea o mediterranea.

____________________________________________________________________________________________________________________________________
____________________________________________________________________________________________________________________________________
____________________________________________________________________________________________________________________________________


## 4) **Oddo et al. (2024)**

**Deep Convolutional LSTM for improved flash flood prediction.**

<https://doi.org/10.3389/frwa.2024.1346104>

Lo studio valuta se l'aggiunta di informazione **spaziale** migliori la previsione idrometrica su un
bacino a risposta molto rapida. Il caso è il Tiber-Hudson di Ellicott City, colpito da due eventi
classificati come millenari nel 2016 e nel 2018.

La variabile prevista è il **livello idrometrico**, a passo **orario**, con 42.384 osservazioni fra
gennaio 2016 e ottobre 2020. Il baseline è una LSTM alimentata dai livelli di due sole stazioni. A
questa viene affiancata una ConvLSTM. Gli input spaziali sono quattro, su griglia 36×48 km a
risoluzione 1 km per NEXRAD, umidità del suolo dal modello Noah, precipitazione
satellitare IMERG, precipitazione accumulata, combinati isolando il contributo
marginale di ciascuno.

Il risultato principale è un miglioramento del ~26% dell'RMSE sugli istanti di piena rispetto al
baseline.

Rispetto agli altri riferimenti, questo lavoro **converge** con la proposta progettuale su alcune
scelte e ne fornisce evidenza sperimentale.

A seguire alciuni punti sostanziali rispetto alla proposta progettuale:

- La risoluzione dei prodotti satellitari ha importanza: ad esempio IMERG e Noah, usati
individualmente, producono gli errori più alti, gli autori attribuiscono il risultato alla loro risoluzione (11–12 km)
rispetto al chilometro dei prodotti da NEXRAD. È un'indicazione sperimentale contro l'inserimento del
dato satellitare a bassa risoluzione come input a monte, utile nelle valutazioni dei dati satellitari eventualmente da utilizzare nella proposta progettuale.

- il vincolo alla granularità temporale è il satellite: gli autori osservano che dati idrometrici
sub-orari sarebbero disponibili, ma che il fattore limitante è la frequenza delle osservazioni
satellitari. È il principio alla base della proposta progettuale a due fasi: la scala veloce resta a
terra, il satellite descrive lo sfondo su un'inerzia diversa.

- la direzione futura indicata è la Fase 2: fra gli sviluppi gli autori indicano l'aggiunta di
caratteristiche, come la copertura del suolo, da aggiungere alla metodologia.


- orizzonte: la previsione è a **t+1 ora**, un solo passo. La proposta progettuale ha come obiettivo anche la valutare la
degradazione lungo l'orizzonte temporale previsionale, nella proposta si parla di previsione multi orizzonte che è comunque oggettodi misura.

- estensione della rete: lo studio utilizza due sole stazioni idrometriche su un singolo bacino.
La proposta progettuale prevede di lavorare sulla rete regionale, con un numero di sezioni (quasi 300 stazioni solo in Emilia romagna e oltre 30 bacini)) e una
profondità storica di 15/20 anni (almeno)

- Soglia surrogata invece che ufficiale: l'ente locale dispone di soglie operative dichiarate, ma
la valutazione usa una soglia ricavata statisticamente dai picchi della serie, situata circa 30 cm (1 foot)
**sotto** la prima soglia ufficiale, che identifica 164 istanti di piena. Nella proposta progettuale
il riferimento sono le soglie di criticità ufficiali, non un surrogato statistico.

- Distanza fra metrica di errore e metrica di decisione: il miglioramento del 26% sull'RMSE ai
picchi si traduce in un miglioramento del **6%** nella corretta identificazione degli istanti di
piena, e gli autori riportano un elevato tasso di falsi negativi sia per la ConvLSTM sia per il
baseline. Un guadagno sull'errore quadratico non implica quindi un guadagno equivalente sulla
decisione di allertamento: nella proposta progettuale è quest'ultima a essere misurata direttamente.

- eventi estremi nel training: entrambe le piene storiche ricadono nel periodo di addestramento.
Gli autori eseguono una diagnostica separandole e riportano un **incremento del 52% dell'RMSE** sugli
istanti di piena. È una misura esplicita del divario fra prestazioni in campione e fuori campione
sugli estremi. Nella proposta progettuale la distribuzione degli eventi maggiori fra periodo di
addestramento e periodo di test sarà esplicitata, con una validazione dedicata agli eventi che
eccedono il massimo osservato in addestramento (comunque presenti dato l'intervallo storico ed i bacini considerati, alluvioni evento purtroppo ripetitivo in EmiliaROmagna e in Toscana)

- Quantificazione dell'incertezza: assente nel paper: la valutazione è deterministica e basata su
RMSE con test di significatività rispetto al baseline. Nella proposta progettuale è una componente a
sé stante, indipendente dal modello predittivo e quindi applicabile a qualsiasi architettura.te.

**Elementi da valutare per la proposta progettuale.** Un risultato controintuitivo utile in fase di
progettazione: finestre di input **più corte** (1–2 ore) hanno prodotto errori inferiori rispetto a
finestre più lunghe, comportamento che gli autori attribuiscono alla rapidità di risposta del bacino.
