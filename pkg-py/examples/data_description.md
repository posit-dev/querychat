# Data Dictionary

- **survival**: Survival status  
  - 0 = No  
  - 1 = Yes  

- **pclass**: Ticket class  
  - 1 = 1st class  
  - 2 = 2nd class  
  - 3 = 3rd class  

- **sex**: Sex of the passenger  

- **age**: Age in years  

- **sibsp**: Number of siblings or spouses aboard the Titanic  

- **parch**: Number of parents or children aboard the Titanic  

- **ticket**: Ticket number  

- **fare**: Passenger fare  

- **cabin**: Cabin number  

- **embarked**: Port of embarkation  
  - C = Cherbourg  
  - Q = Queenstown  
  - S = Southampton  

## Variable Notes

- **pclass** is a proxy for socio-economic status (SES):  
  - 1st = Upper class  
  - 2nd = Middle class  
  - 3rd = Lower class  

- **age**:  
  - If less than 1 year old, age is fractional.  
  - Estimated ages are represented as `xx.5`.  

- **sibsp**: Family relations are defined as:  
  - Sibling = brother, sister, stepbrother, stepsister  
  - Spouse = husband, wife (mistresses and fiancés were ignored)  

- **parch**: Family relations are defined as:  
  - Parent = mother, father  
  - Child = daughter, son, stepdaughter, stepson  
  - Some children traveled only with a nanny, so `parch = 0` for them.  