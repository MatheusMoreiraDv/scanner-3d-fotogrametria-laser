# Análise do código-base do scanner laser com Raspberry Pi

Este documento registra a análise inicial do código de referência usado no projeto online Raspberry Pi Laser Scanner. O objetivo não é copiar diretamente a implementação, mas compreender sua lógica, identificar limitações e propor uma reestruturação adequada para um Trabalho de Conclusão de Curso em Ciência da Computação.

## 1. Papel do código-base no projeto

O código-base será usado como referência técnica inicial para compreender:

- controle de motor de passo;
- captura de imagens com Raspberry Pi;
- detecção da linha laser com OpenCV;
- conversão de perfis em pontos tridimensionais;
- geração de arquivo `.obj`.

A implementação principal deste repositório deverá ser reescrita de forma modular, documentada e adaptada ao objetivo de integrar varredura laser e fotogrametria.

## 2. Fluxo geral identificado

O programa original executa o seguinte fluxo:

1. Aguarda o pressionamento de um botão físico.
2. Liga um LED de status.
3. Captura uma imagem da linha laser sobre o objeto.
4. Aplica uma transformação de perspectiva.
5. Filtra a linha vermelha do laser.
6. Extrai pontos da linha detectada.
7. Associa os pontos ao ângulo atual da plataforma.
8. Gira o motor de passo.
9. Repete o processo até completar 360 graus.
10. Converte os pontos para coordenadas cartesianas.
11. Gera uma malha triangular.
12. Exporta o resultado no formato `.obj`.

## 3. Limitações observadas

- Código monolítico.
- Valores de calibração fixos no código.
- Ausência de arquivo de configuração.
- Ausência de separação entre aquisição, processamento e reconstrução.
- Ausência de captura sem laser para fotogrametria.
- Ausência de tratamento robusto de erros.
- Uso de envio por e-mail embutido no código.
- Pouca documentação matemática e computacional.
- Dependência direta de hardware específico.

## 4. Melhorias propostas

A nova implementação deverá:

- separar o controle do motor em um módulo próprio;
- separar a captura de imagens em um módulo próprio;
- criar uma rotina específica para detecção da linha laser;
- salvar metadados de cada experimento;
- capturar imagens com laser ligado e desligado;
- organizar os dados para fotogrametria;
- permitir calibração por arquivo externo;
- gerar nuvem de pontos em formatos simples como `.xyz`, `.csv` e `.ply`;
- gerar malha `.obj` apenas após validação dos pontos;
- documentar todas as hipóteses geométricas adotadas.

## 5. Direção do projeto

A reprodução do scanner laser será tratada como baseline. A contribuição principal do projeto será a construção de um fluxo híbrido, combinando:

- varredura laser para geometria;
- fotogrametria para reconstrução visual;
- comparação experimental entre os dois métodos;
- possível integração dos resultados em etapa avançada.
