import json
import bcrypt
import getpass
from ursina import *
from random import random, randint
import screeninfo
import os

# ========== 登录系统 ==========
USERS_FILE = 'users.json'

def load_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

def register():
    users = load_users()
    username = input("请输入用户名：")
    if username in users:
        print("❌ 用户名已存在！")
        return False
    password = getpass.getpass("请输入密码（不显示）：")
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    users[username] = hashed.decode()
    save_users(users)
    print("✅ 注册成功！")
    return True

def login():
    users = load_users()
    username = input("请输入用户名：")
    password = getpass.getpass("请输入密码（不显示）：")

    if username in users and bcrypt.checkpw(password.encode(), users[username].encode()):
        print("✅ 登录成功！欢迎进入飞行世界！")
        return True
    else:
        print("❌ 登录失败！账号或密码错误")
        return False

def login_menu():
    while True:
        print("\n=== 飞行游戏 登录系统 ===")
        print("1. 登录")
        print("2. 注册")
        print("3. 退出")
        choice = input("请选择操作（1/2/3）：")
        if choice == '1':
            if login():
                return True
        elif choice == '2':
            register()
        elif choice == '3':
            exit()
        else:
            print("无效选择，请重新输入。")

# ========== 启动登录界面 ==========
if not login_menu():
    exit()

# ========== 游戏设置 ==========
monitor = screeninfo.get_monitors()[0]
screen_width, screen_height = monitor.width, monitor.height

window.size = (screen_width // 2, screen_height // 2)
window.position = (100, 100)
window.borderless = False
window.title = "飞行游戏"

app = Ursina()

# ========== 玩家 ==========
class Player(Entity):
    def __init__(self, **kwargs):
        super().__init__(model='cube', color=color.orange, scale=(1,2,1), collider='box', **kwargs)
        self.hp = 100
        self.fly_power = 0
        self.fuel = 100
        self.is_flying = False
        self.fly_effect = Entity(model='quad', texture='fire_texture', scale=(2, 0.5, 1), parent=self, color=color.azure)
        self.model = 'human_model.fbx'
        self.scale = 2
        self.collider = 'mesh'

    def update(self):
        speed = 5 * time.dt
        if held_keys['a']: self.x -= speed
        if held_keys['d']: self.x += speed
        if held_keys['w']: self.z += speed
        if held_keys['s']: self.z -= speed

        if held_keys['space'] and self.fuel > 0:
            self.fly_power = 5
            self.fuel -= 1 * time.dt
            self.is_flying = True
            self.fly_effect.enabled = True
        else:
            self.fly_power -= 4 * time.dt
            self.is_flying = False
            self.fly_effect.enabled = False

        self.y += self.fly_power * time.dt
        if self.y < 1:
            self.y = 1
            self.fly_power = 0

        if self.fuel < 100 and not held_keys['space']:
            self.fuel += 10 * time.dt

        health_text.text = f'HP: {int(self.hp)}'
        fuel_text.text = f'Fuel: {int(self.fuel)}'

    def update_health(self):
        health_text.text = f'HP: {int(self.hp)}'


# ========== 敌人 ==========
class Enemy(Entity):
    def __init__(self, target, **kwargs):
        super().__init__(model='cube', color=color.red, scale=(1,2,1), collider='box', **kwargs)
        self.target = target
        self.alive = True
        self.hp = 40
        self.fly_power = 0
        self.is_flying = False
        self.fly_effect = Entity(model='quad', texture='fire_texture', scale=(2, 0.5, 1), parent=self, color=color.azure)
        self.model = 'human_model_enemy.fbx'
        self.scale = 2
        self.collider = 'mesh'

    def update(self):
        if not self.alive:
            return
        if random() < 0.01:
            self.fly_power = 5
            self.is_flying = True
            self.fly_effect.enabled = True
        else:
            self.fly_power -= 9.8 * time.dt
            self.is_flying = False
            self.fly_effect.enabled = False

        self.y += self.fly_power * time.dt
        if self.y < 1:
            self.y = 1
            self.fly_power = 0

        direction = (self.target.position - self.position).normalized()
        self.position += direction * 4 * time.dt

        if distance_2d(self.position, self.target.position) < 1:
            print("玩家被敌人撞到了！游戏结束！")
            self.target.hp = 0
            self.target.update_health()
            Text(text="你被敌人干掉了！💀", scale=2, color=color.red, origin=(0,0), background=True)
            application.pause()

    def take_damage(self, amount):
        self.hp -= amount
        print(f'敌人受到伤害，当前HP：{self.hp}')
        if self.hp <= 0:
            self.alive = False
            destroy(self)
            check_victory()

# ========== 子弹 ==========
class Bullet(Entity):
    def __init__(self, pos, direction):
        super().__init__(model='sphere', color=color.yellow, scale=0.2, position=pos, collider='sphere')
        self.direction = direction
        self.speed = 10

    def update(self):
        self.position += self.direction * time.dt * self.speed
        for enemy in enemies:
            if enemy.alive and self.intersects(enemy).hit:
                enemy.take_damage(10)
                destroy(self)
                break

# ========== 工具函数 ==========
def distance_2d(p1, p2):
    return ((p1.x - p2.x)**2 + (p1.z - p2.z)**2)**0.5

def check_victory():
    if all(not enemy.alive for enemy in enemies):
        Text(text="你吃鸡了！🎉", scale=3, color=color.yellow, origin=(0,0), background=True)
        application.pause()

def setup_island():
    Entity(model='plane', texture='beach_texture', collider='box', scale=(200, 1, 200))
    [Entity(model='cube', color=color.green, scale=(1,3,1), position=(randint(-100,100),1.5,randint(-100,100)), collider='box') for _ in range(50)]
    [Entity(model='sphere', color=color.gray, scale=(2, 2, 2), position=(randint(-100,100), 1, randint(-100,100))) for _ in range(30)]

# ========== 游戏开始 ==========
player = Player(position=(0, 1, 0))
health_text = Text(text=f'HP: {player.hp}', position=(-0.85, 0.45), origin=(0,0), scale=2)
fuel_text = Text(text=f'Fuel: {player.fuel}', position=(-0.85, 0.38), origin=(0,0), scale=2, color=color.azure)

enemies = [Enemy(target=player, position=(randint(20, 100), 1, randint(20, 100))) for _ in range(10)]

camera.parent = player
camera.position = (0, 5, -15)
camera.rotation_x = 20

setup_island()

def update():
    player.update()
    for enemy in enemies:
        if enemy.alive:
            enemy.update()

def input(key):
    if key == 'm':
        target_enemy = next((e for e in enemies if e.alive), None)
        if not target_enemy:
            return
        bullet_direction = (target_enemy.position - player.position).normalized()
        bullet = Bullet(pos=player.position + Vec3(0, 1, 0), direction=bullet_direction)
        bullet.look_at(target_enemy)

app.run()
