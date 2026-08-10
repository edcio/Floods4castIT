# Soglie & Territorio — allertamento calibrato in due fasi per alluvioni in Italia (inizio da Emilia-Romagna e poi valutazione Toscana)

🚧 **REPO IN COSTRUZIONE** 🚧
Proposta progettuale in fase di impostazione e valutaizione. Nessun modello è ancora implementato:
Documentazione flusso logico proposto.
Il primo contenuto eseguibile è l'esempio esplorativo sui dati della Fase 1 in notebooks/01_processing_eda_fase1.ipynb

---

## Obiettico

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
 │ Uncertainty           │ incertezza applicata │ indice di         │
 │ Quantificazion        │ DOPO il modello      │ PREDISPOSIZIONE   │
 │ (Conformal Prediction)│                      │ per zona di       │
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
