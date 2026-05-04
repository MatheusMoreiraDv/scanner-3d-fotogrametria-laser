# Scanner 3D Híbrido com Raspberry Pi, Laser e Fotogrametria

Este repositório reúne o estudo, a reprodução, a documentação e a evolução de um scanner 3D de baixo custo baseado em Raspberry Pi, plataforma rotativa, câmera, laser de linha e técnicas de fotogrametria.

O projeto nasce como continuidade acadêmica de um plano de bolsa intitulado **Scanner 3D com laser e Raspberry Pi 3**, originalmente voltado ao estudo de microcontroladores, sensores, eletrônica, fotogrametria, aquisição de imagens e validação de escaneamento tridimensional.

A proposta atual amplia o escopo inicial para um trabalho de conclusão de curso ou artigo científico no Bacharelado em Ciência da Computação, com foco em visão computacional, processamento de imagens, sistemas embarcados, reconstrução tridimensional e avaliação experimental.

---

## 1. Objetivo geral

Desenvolver e avaliar um protótipo de scanner 3D híbrido de baixo custo, combinando aquisição automatizada de imagens, varredura com laser de linha e fotogrametria em uma plataforma rotativa controlada por Raspberry Pi.

---

## 2. Objetivos específicos

- Reproduzir um scanner 3D de baixo custo baseado em Raspberry Pi, câmera, laser e plataforma rotativa.
- Automatizar a captura de imagens em diferentes ângulos.
- Processar imagens com laser para extração de perfis geométricos.
- Capturar imagens sem laser para testes de fotogrametria.
- Comparar os resultados obtidos por varredura laser e por fotogrametria.
- Avaliar a qualidade dos modelos tridimensionais gerados.
- Documentar o processo de forma reprodutível para fins didáticos e científicos.

---

## 3. Questão de pesquisa

A combinação entre triangulação laser e fotogrametria pode melhorar a aquisição, validação ou reconstrução tridimensional de objetos em um scanner 3D de baixo custo baseado em Raspberry Pi?

---

## 4. Hipótese inicial

A varredura com laser de linha pode fornecer informações geométricas mais controladas, enquanto a fotogrametria pode fornecer modelos visualmente mais ricos. A combinação dos dois métodos pode permitir um sistema didático mais completo para estudo de visão computacional, reconstrução 3D e sistemas embarcados.

---

## 5. Escopo do projeto

Este projeto não tem como objetivo competir com scanners 3D comerciais. O objetivo é construir um protótipo didático, documentado e reprodutível, capaz de demonstrar os princípios computacionais envolvidos na aquisição e reconstrução tridimensional de objetos.

---

## 6. Metodologia resumida

O sistema será composto por uma plataforma rotativa controlada por motor de passo, uma câmera conectada ao Raspberry Pi e um laser de linha projetado sobre o objeto. Para cada ângulo de rotação, o sistema poderá capturar imagens com laser ligado e com laser desligado.

As imagens com laser serão usadas para extração de perfis da superfície. As imagens sem laser serão usadas em testes de fotogrametria. Os resultados serão comparados por meio de análise visual, medidas dimensionais e, quando possível, comparação entre nuvens de pontos.

---

## 7. Organização do repositório

```text
docs/          Documentação teórica, metodologia, planejamento do TCC e resultados.
src/           Códigos-fonte do sistema.
scripts/       Scripts auxiliares de instalação, captura e processamento.
hardware/      Esquemas, lista de componentes e arquivos relacionados ao protótipo físico.
experiments/   Organização dos experimentos realizados.
data/          Dados brutos, imagens processadas e nuvens de pontos.
notebooks/     Análises exploratórias e visualizações.
paper/         Materiais para possível artigo científico.
```

---

## 8. Fases do projeto

### Fase 1 — Estudo e documentação

* Revisar o projeto original.
* Estudar scanner laser com Raspberry Pi.
* Estudar fotogrametria.
* Estudar calibração de câmera.
* Definir arquitetura do protótipo.

### Fase 2 — Reprodução do scanner base

* Montar a plataforma rotativa.
* Acionar o motor de passo.
* Capturar imagens com a câmera.
* Projetar o laser sobre o objeto.
* Registrar imagens em diferentes ângulos.

### Fase 3 — Processamento da linha laser

* Detectar a linha laser nas imagens.
* Remover ruídos.
* Extrair coordenadas da linha.
* Converter os perfis detectados em pontos 3D aproximados.

### Fase 4 — Fotogrametria

* Capturar imagens sem laser.
* Testar softwares e bibliotecas de fotogrametria.
* Gerar modelos tridimensionais ou nuvens de pontos.

### Fase 5 — Avaliação experimental

* Comparar objetos reais e modelos reconstruídos.
* Medir erros dimensionais.
* Avaliar influência da iluminação, textura e geometria dos objetos.
* Comparar varredura laser e fotogrametria.

### Fase 6 — Escrita do TCC ou artigo

* Consolidar metodologia.
* Organizar resultados.
* Discutir limitações.
* Propor melhorias futuras.

---

## 9. Tecnologias previstas

* Raspberry Pi
* Câmera Raspberry Pi ou câmera USB
* Motor de passo
* Driver de motor
* Laser de linha
* Python
* OpenCV
* NumPy
* Matplotlib
* Softwares de fotogrametria
* Git e GitHub

---

## 10. Cuidados de segurança

O uso de laser exige cuidado. O projeto deverá utilizar laser de baixa potência, evitar exposição direta aos olhos e registrar procedimentos de segurança durante a montagem e os testes.

---

## 11. Licença

Este repositório poderá usar licença MIT para os códigos desenvolvidos e licença Creative Commons para a documentação, desde que sejam respeitados os créditos das referências externas utilizadas no estudo.
