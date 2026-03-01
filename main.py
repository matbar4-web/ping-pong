import pygame
import sys

# Configuration Constants
WIDTH, HEIGHT = 800, 600
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
PADDLE_WIDTH, PADDLE_HEIGHT = 10, 100
BALL_SIZE = 20

# Game Classes
class Paddle:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, PADDLE_WIDTH, PADDLE_HEIGHT)

    def move(self, dy):
        self.rect.y += dy
        if self.rect.top < 0:
            self.rect.top = 0
        if self.rect.bottom > HEIGHT:
            self.rect.bottom = HEIGHT

class Ball:
    def __init__(self):
        self.rect = pygame.Rect(WIDTH // 2 - BALL_SIZE // 2, HEIGHT // 2 - BALL_SIZE // 2, BALL_SIZE, BALL_SIZE)
        self.speed_x = 7
        self.speed_y = 7

    def move(self):
        self.rect.x += self.speed_x
        self.rect.y += self.speed_y

    def bounce(self):
        self.speed_x = -self.speed_x

    def reset(self):
        self.rect.center = (WIDTH // 2, HEIGHT // 2)
        self.speed_x = 7 if self.speed_x < 0 else -7

# Drawing Functions
def draw_window(win, paddles, ball):
    win.fill(BLACK)
    for paddle in paddles:
        pygame.draw.rect(win, WHITE, paddle.rect)
    pygame.draw.ellipse(win, WHITE, ball.rect)
    pygame.display.update()

# Main Game Loop
def main():
    pygame.init()
    win = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Ping Pong Game")
    clock = pygame.time.Clock()

    left_paddle = Paddle(30, HEIGHT // 2 - PADDLE_HEIGHT // 2)
    right_paddle = Paddle(WIDTH - 30 - PADDLE_WIDTH, HEIGHT // 2 - PADDLE_HEIGHT // 2)
    ball = Ball()

    while True:
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        keys = pygame.key.get_pressed()
        if keys[pygame.K_w]:
            left_paddle.move(-10)
        if keys[pygame.K_s]:
            left_paddle.move(10)
        if keys[pygame.K_UP]:
            right_paddle.move(-10)
        if keys[pygame.K_DOWN]:
            right_paddle.move(10)

        ball.move()

        # Ball collision with paddles
        if ball.rect.colliderect(left_paddle.rect) or ball.rect.colliderect(right_paddle.rect):
            ball.bounce()

        # Ball collision with top and bottom
        if ball.rect.top <= 0 or ball.rect.bottom >= HEIGHT:
            ball.speed_y = -ball.speed_y

        # Reset ball if it goes off screen
        if ball.rect.left <= 0 or ball.rect.right >= WIDTH:
            ball.reset()

        draw_window(win, [left_paddle, right_paddle], ball)

if __name__ == '__main__':
    main()