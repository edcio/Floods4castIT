# Primi test di previsione e confronto tra modelli

## Obiettivo

Questa prima fase di lavoro serve a confrontare diversi approcci alla previsione su serie temporali.

Per ora il lavoro è focalizzato su una singola stazione, usando solo i suoi dati per il training e la valutazione. 
Forecast per ora su valore raw rilevato da sensore (a seguire si effettuerà anche sul target a valle della transformation riscalandolo con la soglia rossa di allerta).
Successivamente si andrà ad utilizzare i dati di più stazioni, per verificare se combinarli migliora le previsioni rispetto all'approccio mono-stazione.

L'obiettivo è anche organizzare gli esperimenti in una pipeline di training e validazione riproducibile, con criteri di confronto comuni ai diversi modelli.

## Stato attuale: previsioni mono-stazione

I primi test utilizzano esclusivamente i dati della stazione di Faenza.

Gli approcci attualmente presi in esame sono:

- Persistenza, utilizzata come riferimento per il confronto.
- TimesFM-3.
- CatBoost (con alcune feature di lag e trainig fino al 01/01/2019)

Di seguito sono riportati i primi confronti. I risultati sono ancora preliminari: serviranno ulteriori test e una procedura di validazione comune prima di trarre conclusioni.

### Persistenza

![Grafico delle previsioni con persistenza](docs/img/01_forecast_test/grafico%20solo%20persistenza.png)

### TimesFM-3 e confronto con la persistenza

Per ora la valutazione riguarda un numero limitato di giorni, a causa dei tempi di esecuzione dell'inferenza.

![Grafico di confronto tra TimesFM e persistenza](docs/img/01_forecast_test/TimesFM-grafico%20confronto.png)

![Statistiche di confronto tra TimesFM e persistenza: dettaglio per giorno](docs/img/01_forecast_test/TimesFM-vs-persistenza-stats_giorni_dettaglio.png)

### CatBoost e confronto con la persistenza

Per ora il training è stato eseguito senza hyperparameter tuning su validation set.

Sono già incluse le feature che descrivono la stazione, ma in questi test non permettono di avere particolari effetti, perché i dati utilizzati provengono soltanto da Faenza. Il loro contributo probabilmente valutato quando il training includerà più stazioni.

![Grafico di confronto tra CatBoost e persistenza](docs/img/01_forecast_test/catboost-vs-persistenza.png)

![Statistiche di confronto tra CatBoost e persistenza: riepilogo e dettaglio](docs/img/01_forecast_test/catboost_vs_persistenza_stats_all_e_dettaglio.png)

## Prossime attività

### 1. Completare il confronto mono-stazione

- Approfondire l'architettura e il funzionamento di TimesFM.
- Implementare reti KAN per serie temporali, ad esempio TKAN.
- Implementare una rete LSTM.

### 2. Estendere i test a più stazioni

Effettuare il forecast no soo sul valore raw ma anche su quello riscalato rispetto alle soglie.
Utilizzare i dati di tutte le stazioni per il training e valutare se questo approccio migliora le previsioni rispetto ai modelli addestrati sulla singola stazione.

### 3. Organizzare la pipeline di training e validazione

Riordinare il codice e i confronti, definendo una procedura comune di training e validazione per rendere gli esperimenti riproducibili e i risultati confrontabili.

## Tempistiche

L'obiettivo è completare almeno i test con i dati di più stazioni e i relativi confronti entro la prima settimana di novembre.
