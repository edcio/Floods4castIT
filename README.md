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
 │ (Conformal Prediction)│                      │ per zona di      │
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
                                                      L2 segmentazione U-Net / TorchGeo
                                                      L3 ConvLSTM: stato a t+k giorni
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


## Confronti e valutazioni:

# **1) Nearing et al. (2024) [Google Flood Hub]**
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
