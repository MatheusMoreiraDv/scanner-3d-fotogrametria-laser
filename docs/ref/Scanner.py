# =============================================================================
# ARQUIVO DE REFERÊNCIA — ECE 5725 (Cornell University)
# Autores originais: Michael Xiao (mfx2) e Thomas Scavella (tbs47)
# Título original: 3D Scanner Software
#
# ATENÇÃO: Os comentários em português abaixo NÃO são dos autores originais.
# Foram adicionados pelo Prof. Lucas Sperotto exclusivamente para fins didáticos,
# como material de apoio ao estudo deste código-fonte de referência.
#
# Este arquivo é usado apenas como baseline histórico para análise e
# reimplementação no contexto do TCC/artigo do repositório.
# =============================================================================

"""
VISÃO GERAL DO SISTEMA
======================
Este programa controla um scanner 3D laser baseado em Raspberry Pi.
O funcionamento geral é o seguinte:

  1. Um motor de passo (stepper motor) gira uma plataforma girante.
  2. A cada passo angular, uma câmera fotografa o objeto iluminado por um laser.
  3. O programa detecta a linha do laser na imagem usando visão computacional.
  4. Com a posição angular e o deslocamento da linha laser, calcula coordenadas 3D.
  5. Ao final de uma rotação completa (360°), gera um arquivo de malha 3D (.obj).
  6. O arquivo é enviado por e-mail automaticamente.

Conceito de coordenadas cilíndricas → cartesianas:
  O laser produz uma linha vertical. A posição horizontal do laser na imagem
  equivale à distância radial (d). O ângulo de rotação é theta (θ). A altura
  na imagem é H. Juntos formam coordenadas cilíndricas (H, θ, d), que são
  convertidas para (x, y, z) cartesianas para montar a malha 3D.
"""

# =============================================================================
# IMPORTAÇÕES DE BIBLIOTECAS
# =============================================================================

# Função de transformação de perspectiva implementada em arquivo separado (transform.py)
from transform import four_point_transform

# OpenCV: biblioteca de visão computacional. Usada para ler imagens, filtrar cores
# e detectar a linha do laser.
import cv2

# NumPy: biblioteca de matemática numérica. Usada para trabalhar com arrays
# (matrizes de pixels) de forma eficiente.
import numpy as np

# math: módulo padrão do Python com funções matemáticas como cos() e sin().
import math

# PiCamera: biblioteca para controlar a câmera do Raspberry Pi.
from picamera import PiCamera

# sleep: função que pausa a execução por um número de segundos.
# Usada para aguardar a câmera estabilizar antes de capturar.
from time import sleep

# RPi.GPIO: biblioteca de baixo nível para controlar os pinos GPIO do Raspberry Pi.
# GPIO = General Purpose Input/Output (Entrada/Saída de Propósito Geral).
import RPi.GPIO as GPIO

# time: módulo de tempo — usado para pausas precisas (time.sleep).
import time

# os: módulo para interagir com o sistema operacional (não usado diretamente aqui,
# mas é uma importação comum em projetos com arquivos).
import os

# gpiozero: biblioteca de mais alto nível para GPIO, mais simples que RPi.GPIO.
# LED: controla um LED simples (ligado/desligado).
# PWMLED: controla um LED com PWM (Pulse Width Modulation — variação de brilho).
# Button: detecta o estado de um botão (pressionado ou não).
from gpiozero import LED
from gpiozero import PWMLED
from gpiozero import Button

# smtplib e email.*: bibliotecas padrão do Python para enviar e-mails via SMTP.
# SMTP = Simple Mail Transfer Protocol (protocolo de envio de e-mail).
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders


# =============================================================================
# CONFIGURAÇÃO DOS PINOS DO MOTOR DE PASSO (STEPPER MOTOR)
# =============================================================================
# O motor de passo é controlado por 4 fios (bobinas). Cada pino GPIO envia
# um sinal HIGH (5V) ou LOW (0V) para energizar uma bobina específica.
# A sequência de ativação das bobinas define a direção e velocidade do motor.
#
# Os números abaixo são os números dos pinos no esquema BCM (Broadcom),
# que é a numeração dos chips do Raspberry Pi (diferente da posição física).
out1 = 13   # Bobina 1 do motor
out2 = 16   # Bobina 2 do motor
out3 = 5    # Bobina 3 do motor
out4 = 12   # Bobina 4 do motor

# =============================================================================
# CONFIGURAÇÃO DE PERIFÉRICOS ADICIONAIS (BOTÃO E LED)
# =============================================================================
# Botão conectado ao pino GPIO 23 — usado para iniciar o processo de varredura.
button = Button(26)

# LED com controle PWM no pino GPIO 18.
# PWM permite variar o brilho do LED (0% = apagado, 100% = máximo brilho).
# O método .pulse() faz o LED piscar suavemente como indicação de status.
led = PWMLED(6)

# Variável de controle do estado atual do motor de passo.
# O motor possui 8 posições (estados 0 a 7) na sequência half-step.
# Esta variável rastreia em qual estado o motor se encontra entre os passos.
i = 0

# =============================================================================
# INICIALIZAÇÃO DOS PINOS GPIO (modo de baixo nível, via RPi.GPIO)
# =============================================================================
# GPIO.BCM = usa a numeração BCM dos pinos (padrão mais comum em projetos).
GPIO.setmode(GPIO.BCM)

# Configura cada pino do motor como SAÍDA (OUTPUT), pois o Raspberry Pi
# vai enviar sinais para o motor (e não receber sinais de fora).
GPIO.setup(out1, GPIO.OUT)
GPIO.setup(out2, GPIO.OUT)
GPIO.setup(out3, GPIO.OUT)
GPIO.setup(out4, GPIO.OUT)


# =============================================================================
# CLASSE: vertex (vértice 3D)
# =============================================================================
# Em Python, uma "classe" é um molde para criar objetos com propriedades e ações.
# Esta classe representa um ponto no espaço tridimensional com coordenadas (x, y, z).
class vertex:
    def __init__(self, x, y, z):
        """
        Construtor: chamado automaticamente ao criar um novo vértice.
        __init__ é o método especial de inicialização de classes em Python.
        self = referência ao próprio objeto que está sendo criado.
        """
        self.x = x  # Coordenada X (largura / eixo horizontal)
        self.y = y  # Coordenada Y (profundidade / eixo de rotação)
        self.z = z  # Coordenada Z (altura / eixo vertical)

    def write(self):
        """
        Retorna o vértice no formato do arquivo .OBJ (formato 3D padrão).
        O prefixo "v" indica que é um vértice no padrão Wavefront OBJ.
        Exemplo de saída: "v 10 -5 30"
        """
        return "v " + str(self.x) + " " + str(self.y) + " " + str(self.z)


# =============================================================================
# CLASSE: face (triângulo da malha 3D)
# =============================================================================
# Uma malha 3D (mesh) é formada por vértices conectados em triângulos.
# Cada triângulo é chamado de "face". Esta classe representa uma face
# definida por 3 índices de vértices (v1, v2, v3).
class face:
    def __init__(self, v1, v2, v3):
        """
        Os parâmetros v1, v2, v3 são os ÍNDICES (posições na lista de vértices)
        dos três vértices que formam este triângulo.
        """
        self.v1 = v1
        self.v2 = v2
        self.v3 = v3

    def write(self):
        """
        Retorna a face no formato do arquivo .OBJ.
        O prefixo "f" indica que é uma face no padrão Wavefront OBJ.
        Exemplo de saída: "f 1 2 3"
        """
        return "f " + str(self.v1) + " " + str(self.v2) + " " + str(self.v3)


# =============================================================================
# FUNÇÃO: getVertex — converte coordenadas cilíndricas em cartesianas
# =============================================================================
def getVertex(pCoord):
    """
    O scanner mede pontos em coordenadas CILÍNDRICAS:
      H = altura (eixo vertical)
      t = ângulo theta em radianos (posição angular da rotação)
      d = distância radial (deslocamento lateral do laser na imagem)

    Para criar a malha 3D, precisamos de coordenadas CARTESIANAS (x, y, z).
    A conversão usa trigonometria básica:
      x = d * cos(θ)   → projeção horizontal
      y = d * sin(θ)   → projeção em profundidade
      z = H            → altura permanece igual

    Imagine um círculo: para qualquer ponto na borda (raio d, ângulo θ),
    as coordenadas x e y são exatamente d*cos(θ) e d*sin(θ).
    """
    H = pCoord.x   # Altura do ponto (linha da imagem relativa ao fundo)
    t = pCoord.y   # Ângulo θ em radianos
    d = pCoord.z   # Distância radial (deslocamento do laser do centro)

    x = d * math.cos(t)   # Coordenada X cartesiana
    y = d * math.sin(t)   # Coordenada Y cartesiana
    z = H                  # Coordenada Z = altura

    # int() converte para inteiro, pois o formato .OBJ espera números inteiros aqui
    return vertex(int(x), int(y), int(z))


# =============================================================================
# FUNÇÃO: step — move o motor de passo x posições
# =============================================================================
def step(x, i):
    """
    Controla o motor de passo usando sequência half-step de 8 fases.

    CONCEITO DE MOTOR DE PASSO:
    Um motor de passo (stepper motor) gira em incrementos fixos ("passos")
    ao invés de girar continuamente. Cada passo é ativado energizando as
    bobinas em uma sequência específica.

    HALF-STEP (meio-passo):
    Na sequência half-step, alternamos entre ativar 1 bobina (passo inteiro)
    e 2 bobinas ao mesmo tempo (meio-passo). Isso dobra a resolução angular.
    A sequência completa tem 8 estados (i = 0 a 7):

      Estado | out1 | out2 | out3 | out4
      -------|------|------|------|-----
         0   | HIGH |  LOW |  LOW |  LOW   ← apenas bobina 1
         1   | HIGH | HIGH |  LOW |  LOW   ← bobinas 1 e 2
         2   |  LOW | HIGH |  LOW |  LOW   ← apenas bobina 2
         3   |  LOW | HIGH | HIGH |  LOW   ← bobinas 2 e 3
         4   |  LOW |  LOW | HIGH |  LOW   ← apenas bobina 3
         5   |  LOW |  LOW | HIGH | HIGH   ← bobinas 3 e 4
         6   |  LOW |  LOW |  LOW | HIGH   ← apenas bobina 4
         7   | HIGH |  LOW |  LOW | HIGH   ← bobinas 4 e 1

    Para girar para frente: percorre 0→1→2→3→4→5→6→7→0→...
    Para girar para trás:   percorre 0→7→6→5→4→3→2→1→0→...

    PARÂMETROS:
      x: número de passos a avançar (positivo = frente, negativo = trás)
         limitado a ±400 por segurança
      i: estado atual do motor (0 a 7)

    RETORNO:
      Novo valor de i após os passos (para uso na próxima chamada)
    """
    positive = 0   # Flag: 1 se o último movimento foi para frente
    negative = 0   # Flag: 1 se o último movimento foi para trás
    y = 0

    # Desliga todas as bobinas antes de iniciar a sequência
    GPIO.output(out1, GPIO.LOW)
    GPIO.output(out2, GPIO.LOW)
    GPIO.output(out3, GPIO.LOW)
    GPIO.output(out4, GPIO.LOW)

    # --- MOVIMENTO PARA FRENTE (x positivo) ---
    if x > 0 and x <= 400:
        # range(x, 0, -1) conta de x até 1 (decrementando) — é um loop de x iterações
        for y in range(x, 0, -1):

            # Se veio de movimento reverso, ajusta o estado antes de prosseguir
            if negative == 1:
                if i == 7:
                    i = 0
                else:
                    i = i + 1
                y = y + 2
                negative = 0

            positive = 1

            # Aplica o padrão de bobinas correspondente ao estado atual i
            if i == 0:
                GPIO.output(out1, GPIO.HIGH)
                GPIO.output(out2, GPIO.LOW)
                GPIO.output(out3, GPIO.LOW)
                GPIO.output(out4, GPIO.LOW)
                time.sleep(0.03)   # Pausa de 30ms entre passos (define a velocidade)
            elif i == 1:
                GPIO.output(out1, GPIO.HIGH)
                GPIO.output(out2, GPIO.HIGH)
                GPIO.output(out3, GPIO.LOW)
                GPIO.output(out4, GPIO.LOW)
                time.sleep(0.03)
            elif i == 2:
                GPIO.output(out1, GPIO.LOW)
                GPIO.output(out2, GPIO.HIGH)
                GPIO.output(out3, GPIO.LOW)
                GPIO.output(out4, GPIO.LOW)
                time.sleep(0.03)
            elif i == 3:
                GPIO.output(out1, GPIO.LOW)
                GPIO.output(out2, GPIO.HIGH)
                GPIO.output(out3, GPIO.HIGH)
                GPIO.output(out4, GPIO.LOW)
                time.sleep(0.03)
            elif i == 4:
                GPIO.output(out1, GPIO.LOW)
                GPIO.output(out2, GPIO.LOW)
                GPIO.output(out3, GPIO.HIGH)
                GPIO.output(out4, GPIO.LOW)
                time.sleep(0.03)
            elif i == 5:
                GPIO.output(out1, GPIO.LOW)
                GPIO.output(out2, GPIO.LOW)
                GPIO.output(out3, GPIO.HIGH)
                GPIO.output(out4, GPIO.HIGH)
                time.sleep(0.03)
            elif i == 6:
                GPIO.output(out1, GPIO.LOW)
                GPIO.output(out2, GPIO.LOW)
                GPIO.output(out3, GPIO.LOW)
                GPIO.output(out4, GPIO.HIGH)
                time.sleep(0.03)
            elif i == 7:
                GPIO.output(out1, GPIO.HIGH)
                GPIO.output(out2, GPIO.LOW)
                GPIO.output(out3, GPIO.LOW)
                GPIO.output(out4, GPIO.HIGH)
                time.sleep(0.03)

            # Avança para o próximo estado; reinicia do 0 após o estado 7 (ciclo)
            if i == 7:
                i = 0
                continue
            i = i + 1

    # --- MOVIMENTO PARA TRÁS (x negativo) ---
    elif x < 0 and x >= -400:
        x = x * -1   # Torna x positivo para usar no range()

        for y in range(x, 0, -1):

            # Se veio de movimento positivo, ajusta o estado antes de prosseguir
            if positive == 1:
                if i == 0:
                    i = 7
                else:
                    i = i - 1
                y = y + 3
                positive = 0

            negative = 1

            # Aplica o mesmo padrão de bobinas (a lógica é idêntica ao forward,
            # a diferença está no sentido de incremento de i ao final do loop)
            if i == 0:
                GPIO.output(out1, GPIO.HIGH)
                GPIO.output(out2, GPIO.LOW)
                GPIO.output(out3, GPIO.LOW)
                GPIO.output(out4, GPIO.LOW)
                time.sleep(0.03)
            elif i == 1:
                GPIO.output(out1, GPIO.HIGH)
                GPIO.output(out2, GPIO.HIGH)
                GPIO.output(out3, GPIO.LOW)
                GPIO.output(out4, GPIO.LOW)
                time.sleep(0.03)
            elif i == 2:
                GPIO.output(out1, GPIO.LOW)
                GPIO.output(out2, GPIO.HIGH)
                GPIO.output(out3, GPIO.LOW)
                GPIO.output(out4, GPIO.LOW)
                time.sleep(0.03)
            elif i == 3:
                GPIO.output(out1, GPIO.LOW)
                GPIO.output(out2, GPIO.HIGH)
                GPIO.output(out3, GPIO.HIGH)
                GPIO.output(out4, GPIO.LOW)
                time.sleep(0.03)
            elif i == 4:
                GPIO.output(out1, GPIO.LOW)
                GPIO.output(out2, GPIO.LOW)
                GPIO.output(out3, GPIO.HIGH)
                GPIO.output(out4, GPIO.LOW)
                time.sleep(0.03)
            elif i == 5:
                GPIO.output(out1, GPIO.LOW)
                GPIO.output(out2, GPIO.LOW)
                GPIO.output(out3, GPIO.HIGH)
                GPIO.output(out4, GPIO.HIGH)
                time.sleep(0.03)
            elif i == 6:
                GPIO.output(out1, GPIO.LOW)
                GPIO.output(out2, GPIO.LOW)
                GPIO.output(out3, GPIO.LOW)
                GPIO.output(out4, GPIO.HIGH)
                time.sleep(0.03)
            elif i == 7:
                GPIO.output(out1, GPIO.HIGH)
                GPIO.output(out2, GPIO.LOW)
                GPIO.output(out3, GPIO.LOW)
                GPIO.output(out4, GPIO.HIGH)
                time.sleep(0.03)

            # Recua para o estado anterior; ao chegar em 0, vai para 7 (ciclo reverso)
            if i == 0:
                i = 7
                continue
            i = i - 1

    return i   # Retorna o estado atual do motor para ser usado na próxima chamada


# =============================================================================
# LOOP PRINCIPAL DO SCANNER
# =============================================================================
# while(1) é um loop infinito — o sistema fica esperando por varreduras
# indefinidamente, até que o programa seja interrompido manualmente.
while (1):

    # --- PARÂMETROS DA VARREDURA ---

    # numItt = número de iterações (fotografias) em uma rotação de 360°.
    # Com 20 iterações, o motor gira 360/20 = 18° entre cada foto.
    numItt = 20

    # Ângulo inicial da varredura (graus)
    theta = 0

    # Incremento angular por iteração (graus)
    thetaInc = 360.0 / numItt   # = 18.0 graus por passo

    # Posição atual do motor em número de passos
    motorPos = 0

    # Quantos passos o motor deve avançar a cada iteração.
    # 400 passos = uma volta completa para este motor (com half-step).
    motorPosI = 400.0 / numItt   # = 20 passos por iteração

    # Lista que acumula todos os pontos 3D de todas as iterações
    meshPoints = []

    # Lista com o número de pontos em cada "fatia" (coluna de varredura)
    lineLenth = []

    # --- AGUARDA PRESSIONAMENTO DO BOTÃO PARA INICIAR ---
    # O programa fica travado neste loop enquanto o botão não for pressionado.
    while (not button.is_pressed):
        sleep(0.1)   # Verifica o botão a cada 100ms para não sobrecarregar o processador

    # Acende o LED pulsante para indicar que a varredura está em andamento
    led.pulse()

    # ==========================================================================
    # LOOP DE VARREDURA: captura uma imagem a cada passo angular
    # ==========================================================================
    while (theta < 360):

        # --- CAPTURA DA IMAGEM ---
        # Inicializa a câmera, aguarda estabilização, captura e fecha.
        # A câmera é aberta e fechada a cada iteração para liberar recursos.
        camera = PiCamera()
        camera.start_preview()
        sleep(1)   # 1 segundo para a câmera ajustar exposição e foco
        camera.capture('lineDetection.jpg')   # Salva a foto no disco
        camera.close()

        # Carrega a imagem do disco como um array NumPy (matriz de pixels BGR)
        img = cv2.imread('lineDetection.jpg')

        # --- CORREÇÃO DE PERSPECTIVA ---
        # A câmera não está perfeitamente alinhada com o objeto, então a imagem
        # sofre distorção de perspectiva. Os 4 pontos abaixo definem os cantos
        # da região de interesse (ROI) na imagem original:
        #   tlp = top-left point    (canto superior esquerdo)
        #   trp = top-right point   (canto superior direito)
        #   brp = bottom-right point (canto inferior direito)
        #   blp = bottom-left point  (canto inferior esquerdo)
        # A função four_point_transform "endireita" a perspectiva, como se
        # você estivesse olhando de frente para a cena.
        tlp = (375.0, 275.0)
        trp = (1090.0, 420.0)
        brp = (1090.0, 915.0)
        blp = (375.0, 1060.0)
        pts = np.array([tlp, trp, brp, blp])
        img = four_point_transform(img, pts)

        # --- FILTRO DE COR: detecta o laser vermelho ---
        # O laser é vermelho, então buscamos pixels com alto valor no canal B
        # (atenção: OpenCV usa ordem BGR, não RGB!).
        # lowerb e upperb definem o intervalo de cor aceitável.
        # Aqui o filtro captura pixels com B > 50 (inclui brancos e azuis também —
        # calibração específica para o ambiente deste projeto).
        lowerb = np.array([50, 0, 0])       # Limite inferior (B, G, R)
        upperb = np.array([255, 255, 255])  # Limite superior (sem restrição G e R)

        # cv2.inRange: cria uma imagem binária (0 ou 255) onde os pixels dentro
        # do intervalo de cor ficam brancos (255) e os demais ficam pretos (0).
        red_line = cv2.inRange(img, lowerb, upperb)

        # --- EXTRAÇÃO DA LINHA DO LASER ---
        # h, w = altura e largura da imagem em pixels
        h, w = np.shape(red_line)

        # Cria uma matriz de zeros (imagem preta) do mesmo tamanho
        backG = np.zeros((h, w))

        # bottomR rastreia a linha mais baixa onde o laser foi detectado
        bottomR = 0

        r = 0  # Índice da linha (row) atual

        # np.argmax(red_line, axis=1): para cada LINHA da imagem, retorna o índice
        # da COLUNA com o maior valor. Como red_line é binária (0 ou 255),
        # isso encontra a coluna do pixel mais à direita do laser em cada linha.
        for cIndex in np.argmax(red_line, axis=1):
            # Verifica se o pixel encontrado realmente pertence ao laser (valor != 0)
            if red_line[r, cIndex] != 0:
                backG[r, cIndex] = 1   # Marca este pixel como parte da linha laser
                bottomR = r            # Atualiza a linha mais baixa detectada
            r += 1

        # --- CÁLCULO DAS COORDENADAS CILÍNDRICAS ---
        tempV = []      # Lista temporária de coordenadas desta iteração
        r = 0

        # centerC = coluna central da imagem (referência para calcular deslocamento)
        # O deslocamento do laser em relação ao centro indica a distância ao objeto.
        centerC = 420.0

        for cIndex in np.argmax(backG, axis=1):
            if backG[r, cIndex] == 1:
                # H = altura relativa ao fundo do objeto (bottomR é o "chão")
                H = r - bottomR

                # dist = deslocamento horizontal do laser em relação ao centro
                # Valores negativos = laser à esquerda do centro (objeto mais próximo)
                dist = cIndex - centerC

                # Cria um "vértice" em coordenadas cilíndricas:
                #   x = H (altura)
                #   y = ângulo em radianos
                #   z = distância radial
                # Atenção: aqui a classe vertex é usada temporariamente para
                # armazenar coordenadas cilíndricas, não cartesianas ainda.
                coord = vertex(H, np.radians(theta), dist)
                tempV.append(coord)
            r += 1

        # --- SUBAMOSTRAGEM VERTICAL ---
        # Para não gerar malhas enormes, pega apenas 20 pontos por fatia,
        # distribuídos uniformemente ao longo da altura.
        intv = 20
        intv = len(tempV) / intv   # Intervalo entre pontos selecionados

        if len(tempV) != 0 and intv != 0:
            V = []
            V.append(tempV[0])   # Sempre inclui o primeiro ponto

            # Inclui um ponto a cada 'intv' posições
            for ind in range(1, len(tempV) - 2):
                if ind % intv == 0:
                    V.append(tempV[ind])

            V.append(tempV[(len(tempV) - 1)])   # Sempre inclui o último ponto

            meshPoints.append(V)
            print(str(len(V)))

            # Armazena o comprimento negativo para facilitar a busca pelo menor
            # (o truque de usar negativo serve para usar np.argmax como argmin)
            lineLenth.append(-1 * len(V))

        # Avança o ângulo e move o motor para a próxima posição
        theta += thetaInc
        i = step(int(motorPosI), i)
        time.sleep(0.3)   # Aguarda o motor estabilizar

    # ==========================================================================
    # MONTAGEM DA MALHA 3D (MESH)
    # ==========================================================================

    # Para montar triângulos entre "fatias" adjacentes, todas as fatias precisam
    # ter o mesmo número de pontos. Encontra a fatia com menos pontos.
    # np.argmax(lineLenth) retorna o índice do maior valor em lineLenth.
    # Como os comprimentos estão negativos, o "maior" negativo é o menor positivo.
    shortest = len(meshPoints[np.argmax(lineLenth)])
    print(shortest)   # NOTA: o código original usava "print shortest" (Python 2, sem parênteses)

    # Remove pontos extras de cada fatia até que todas tenham o mesmo tamanho
    for line in meshPoints:
        while len(line) > shortest:
            # Remove o penúltimo ponto (preserva o último como âncora)
            line.pop(len(line) - 2)

    # --- CRIAÇÃO DOS VÉRTICES E FACES ---
    points = []    # Lista de todos os vértices cartesianos
    faces = []     # Lista de todos os triângulos (faces)
    firstRow = []  # Índices dos vértices da primeira fatia (para fechar o cilindro)
    prevRow = []   # Índices dos vértices da fatia anterior

    # Processa a primeira fatia — converte de cilíndrico para cartesiano
    for index in range(1, len(meshPoints[0]) + 1):
        points.append(getVertex(meshPoints[0][index - 1]))
        firstRow.append(index)   # Armazena os índices (começam em 1 no formato OBJ)

    prevRow = firstRow

    # Para cada fatia seguinte, cria triângulos conectando-a à fatia anterior.
    # Cada quadrilátero entre duas fatias é dividido em 2 triângulos:
    #
    #   tr ---- br       tr = top-right    (fatia anterior, ponto superior)
    #   |  \  f2 |       br = bottom-right (fatia anterior, ponto inferior)
    #   | f1 \   |       tl = top-left     (fatia atual, ponto superior)
    #   tl ---- bl       bl = bottom-left  (fatia atual, ponto inferior)
    #
    #   Triângulo f1 = (tl, tr, bl)
    #   Triângulo f2 = (bl, tr, br)

    for col in range(0, len(meshPoints)):
        if col != 0:
            indexS = prevRow[-1]   # Índice do último vértice inserido até agora
            currentRow = []

            for point in range(0, len(meshPoints[col]) - 1):
                tl = indexS + point + 1       # Índice do ponto atual (fatia nova)
                bl = tl + 1                   # Índice do próximo ponto (fatia nova)
                tr = prevRow[point]            # Índice do ponto equivalente (fatia anterior)
                br = prevRow[point + 1]        # Índice do próximo ponto (fatia anterior)

                f1 = face(tl, tr, bl)   # Primeiro triângulo do quadrilátero
                f2 = face(bl, tr, br)   # Segundo triângulo do quadrilátero
                faces.append(f1)
                faces.append(f2)

                points.append(getVertex(meshPoints[col][point]))
                currentRow.append(tl)

                # Se for o último ponto da fatia, adiciona também o ponto final
                if point == len(meshPoints[col]) - 2:
                    points.append(getVertex(meshPoints[col][point + 1]))
                    currentRow.append(bl)

                # Na última fatia, fecha o cilindro conectando de volta à primeira fatia
                if col == (len(meshPoints) - 1):
                    tr = tl
                    br = bl
                    tl = firstRow[point]
                    bl = firstRow[point + 1]
                    f1 = face(tl, tr, bl)
                    f2 = face(bl, tr, br)
                    faces.append(f1)
                    faces.append(f2)

            prevRow = currentRow

    # ==========================================================================
    # EXPORTAÇÃO DO ARQUIVO .OBJ
    # ==========================================================================
    # O formato Wavefront OBJ é um formato de texto simples para malhas 3D.
    # Cada linha começa com "v" (vértice) ou "f" (face/triângulo).
    # Pode ser aberto em Blender, MeshLab, entre outros softwares 3D.
    filetowrite = '3d.obj'
    with open(filetowrite, 'w') as file:
        for point in points:
            file.write(point.write() + "\n")   # Escreve cada vértice
        for f in faces:
            file.write(f.write() + "\n")       # Escreve cada face
        file.close()

    # ==========================================================================
    # ENVIO DO ARQUIVO POR E-MAIL (via Gmail SMTP)
    # ==========================================================================
    # SMTP = Simple Mail Transfer Protocol. O Gmail usa a porta 587 com STARTTLS
    # (protocolo de criptografia para comunicação segura).
    #
    # ATENÇÃO: credenciais em texto plano no código são uma má prática de segurança.
    # Em produção, use variáveis de ambiente ou arquivos de configuração protegidos.
    email_user = 'emailplaceholder'          # Remetente (conta Gmail)
    email_password = 'passwordplaceholder'   # Senha do remetente
    email_send = 'mfx2@cornell.edu'          # Destinatário

    subject = '3D File :) !'

    # MIMEMultipart: permite criar e-mails com corpo de texto E anexos
    msg = MIMEMultipart()
    msg['From'] = email_user
    msg['To'] = email_send
    msg['Subject'] = subject

    body = 'Hi there, here is your 3D mesh file!'
    msg.attach(MIMEText(body, 'plain'))   # Adiciona o corpo do e-mail como texto simples

    # Abre o arquivo .obj em modo binário ('rb') para anexar ao e-mail
    filename = '3d.obj'
    attachment = open(filename, 'rb')

    # MIMEBase: representa o anexo como dados binários genéricos
    part = MIMEBase('application', 'octet-stream')
    part.set_payload((attachment).read())
    encoders.encode_base64(part)   # Codifica em Base64 (formato padrão para anexos)
    part.add_header('Content-Disposition', "attachment; filename= " + filename)

    msg.attach(part)

    # Conecta ao servidor SMTP do Gmail, autentica e envia
    text = msg.as_string()
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()                          # Inicia criptografia TLS
    server.login(email_user, email_password)   # Autentica com usuário e senha
    server.sendmail(email_user, email_send, text)
    server.quit()   # Encerra a conexão com o servidor

    # Apaga o LED para indicar que a varredura foi concluída
    led.off()

    # TODO: enviar dados para servidor online
    # TODO: limpar variáveis entre varreduras


# =============================================================================
# LIMPEZA DOS GPIO AO ENCERRAR O PROGRAMA
# =============================================================================
# GPIO.cleanup() é OBRIGATÓRIO ao terminar um programa que usa GPIO.
# Ele reseta todos os pinos para o estado padrão (entrada, sem pull-up/down),
# evitando que pinos fiquem energizados acidentalmente após o programa encerrar.
GPIO.cleanup()
