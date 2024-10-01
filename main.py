from flask import render_template, redirect, url_for, request, flash, Blueprint
from werkzeug.security import check_password_hash, generate_password_hash
from form import FormAuditPush, FormAuthPush
from flask_login import login_user, login_required, logout_user, current_user
from python.run_bot import bot
import disnake
import random
import string
import datetime

# создание блюпринта
main = Blueprint('main', __name__)

# главная страница
@main.route('/')
def index():
  return render_template('index.html')

# Логирование
@main.route('/auth', methods=['POST', 'GET'])
def auth():
  from __init__ import db, Users
  form = FormAuthPush()

  if current_user.is_authenticated:
      return redirect(url_for('main.profile'))

  if form.validate_on_submit():
      static = Users.query.filter_by(static=form.static.data).first()

      if static:
          if static.action == 'Dismissal':
              # Отказ в доступе, если действие 'Dismissal'
              logout_user()  # Закрываем сессию логирования
              flash("Отказано в доступе: вы не состоите во фракции.")
              
          
          # Проверяем пароль, если действие не 'Dismissal'
          if check_password_hash(static.password, form.password.data):
              login_user(static)

              next_url = request.args.get('next')
              if next_url:
                  return redirect(next_url)
              else:
                  return redirect(url_for('main.profile'))
          else:
              flash("Неверный static или password!")
      else:
          flash("Пользователь не найден!")

  return render_template('auth.html', form=form)

# перенаправление на страницу
@main.after_request
def redirect_login(response):
    if response.status_code == 401:
        return redirect(url_for('main.auth') + '?next=' + request.url)

    return response


# Кадровый аудит
@main.route('/audit', methods=['POST', 'GET'])
@login_required
async def audit():
  from __init__ import db, Users, ActionUsers
  form = FormAuditPush()  # Assuming you have a FormAuditPush class defined
  
  # получение изменения ка от конкретного юзера
  action_users = []
  action_users = ActionUsers.query.filter_by(static=current_user.static).all()
  userof = ''
  
  if action_users:
    for item in action_users:
      userof = Users.query.filter_by(static=item.staticof).first()

  user_curr = Users.query.filter_by(static=current_user.static).first()     
  if user_curr:
    organ = user_curr.organ
    nikname = user_curr.nikname
    
    if organ == 'LSPD':
      color = '#142c77'  # Синий
    elif organ == 'LSCSD':
      color = '#9F4C0F'  # Коричневый
    elif organ == 'SANG':
      color = '#166c0e'  # Зеленый
    elif organ == 'FIB':
      color = '#008000' # черный
    elif organ == 'EMS':
      color = '#a21726' # красный
    elif organ == 'GOV':
      color = '#dbbb0b' #

  # проверка валидации формы
  if form.validate_on_submit():
    static = form.static.data
    action = form.action.data
    discord_name = form.discordName.data
    discord_id = form.discordID.data

    user = Users.query.filter_by(static=static).first()
    user_curr = Users.query.filter_by(static=current_user.static).first()
    # проверка action invite на существование статика, если есть то ошибка
    if action == 'Invite':
        if user and user.action == 'Dismissal':
            timespan = datetime.datetime.now()
             
            # получение фракции от юзера который пишет ка
            if user_curr:
              organ_curr = user_curr.organ

            # создание первоначального пароля
            characters = string.ascii_letters + string.digits + string.punctuation
            password = ''.join(random.choice(characters) for i in range(10))
            print(password)
            
            # хэшированиие пароля
            hash_password = generate_password_hash(password)
            await bot.check_updates(password, discord_id)

            # изменение существущей строки
            user.password = hash_password
            user.prevrank = '0'
            user.rankuser = '1'
            user.action = 'Invite'
            user.organ = organ_curr
            user.timespan = timespan
            user.nikname = form.nikname.data

            # создание изменения ка
            new_action_curr_user = ActionUsers(discordid=current_user.discordid, discordname=current_user.discordname, static=current_user.static, nikname=current_user.nikname, timespan=timespan, staticof=user.static, actionof=action, currrankof='1', prevrankof='0')
            
            db.session.add(new_action_curr_user)
            db.session.commit()
          
            flash('Успешно!', 'success')
            return redirect(url_for('main.audit'))
          
        # если в базе отстуствует запись о пользователя
        elif user is None:
          existing_discordID = Users.query.filter_by(discordid=discord_id).all()
          existing_discordName = Users.query.filter_by(discordname=discord_name).all()
          
          # проверка на более двух дс во фракции
          if len(existing_discordName) > 1 or len(existing_discordID) > 1:
            flash('Данный дискорд уже состоит в 2-ух гос. структурах!', 'error')
            return redirect(url_for('main.audit'))
          
          else:
              # создание первоначального пароля
              characters = string.ascii_letters + string.digits + string.punctuation
              password = ''.join(random.choice(characters) for i in range(10))

              await bot.check_updates(password, discord_id)
              timespan = datetime.datetime.now()
              hash_password = generate_password_hash(password)
              
              # получение фракции юзера который пишет ка 
              user_curr = Users.query.filter_by(static=current_user.static).first() 
              if user_curr:
                organ_curr = user_curr.organ
                
              # создание нового юзера  
              new_user = Users(discordid=discord_id, discordname=discord_name, static=static, nikname=form.nikname.data, action=action, organ=organ_curr, prevrank='1', rankuser=form.rank.data, timespan=timespan, password=hash_password)

              new_action_curr_user = ActionUsers(discordid=current_user.discordid, discordname=current_user.discordname, static=current_user.static, nikname=current_user.nikname, timespan=timespan, staticof=static, actionof=action, currrankof='1', prevrankof='0')
              
              db.session.add(new_action_curr_user)
              db.session.add(new_user)
              db.session.commit()
              
              flash('Успешно!', 'success')
              return redirect(url_for('main.audit'))
            
        else:
          flash('Такой статик уже имеется во госс. фракции!', 'error')
          return redirect(url_for('main.audit'))
                  
    else:
        # actions (Raising, Demotion, Dismissal) поиск статика на существаония, если нет ошибка
        user = Users.query.filter_by(static=static).first()
        if not user or user.action == 'Dismissal':
            flash('Такого статика не существует во фракции!', 'error')
            return redirect(url_for('main.audit'))
          
        else:
          # увольнение существуещего юзера с фракции
          if action == 'Dismissal':
            timespan = datetime.datetime.now()

            new_action_curr_user = ActionUsers(discordid=current_user.discordid, discordname=current_user.discordname, static=current_user.static, nikname=current_user.nikname, timespan=timespan, staticof=static, actionof=action, currrankof='0', prevrankof=user.rankuser)
            db.session.add(new_action_curr_user)
            
            # перезапись существущей строки 
            prev_rank = user.rankuser
            user.prevrank = prev_rank
            user.rankuser = '0'
            
            user.timespan = timespan
            user.action = 'Dismissal'
            
            db.session.commit()
            flash('Статик успешно уволен', 'success')
            return redirect(url_for('main.audit'))
          
          # повышение существующего юзера во фракции
          elif action == 'Raising':
            prev_rank = user.rankuser
            new_rank = form.rank.data
            
            # проверка новый ранг должен быть больше старого
            if new_rank < prev_rank:
              flash('При повышении, новый ранг не может быть меньше старого')
              return redirect(url_for('main.audit'))

            timespan = datetime.datetime.now()
            new_action_curr_user = ActionUsers(discordid=current_user.discordid, discordname=current_user.discordname, static=current_user.static, nikname=current_user.nikname, timespan=timespan, staticof=static, actionof=action, currrankof=form.rank.data, prevrankof=user.rankuser)
            db.session.add(new_action_curr_user)

            timespan = datetime.datetime.now()
            
            # перезапись существущих данных строки 
            user.prevrank = user.rankuser
            user.action = action
            user.rankuser = new_rank 
            user.timespan = timespan
            user.action = 'Raising'
            
            db.session.commit() 
            flash('Статик успешно повышен', 'success')
            return redirect(url_for('main.audit'))
          
          # понижение сущесвующего юзера во фракции
          elif action == 'Demotion':
            prev_rank = user.rankuser
            new_rank = form.rank.data
            
            if new_rank > prev_rank:
              flash('При понижении, новый ранг не может быть больше старого')
              return redirect(url_for('main.audit'))
            
            timespan = datetime.datetime.now()
            new_action_curr_user = ActionUsers(discordid=current_user.discordid, discordname=current_user.discordname, static=current_user.static, nikname=current_user.nikname, timespan=timespan, staticof=static, actionof=action, currrankof=form.rank.data, prevrankof=user.rankuser)
            db.session.add(new_action_curr_user)
            
            user.action = action
            user.rankuser = new_rank 
            user.timespan = timespan
            user.action = 'Demotion'
            
            db.session.commit() 
            flash('Статик успешно понижен', 'success')
            return redirect(url_for('main.audit'))
          
    return redirect(url_for('main.audit'))

  return render_template('ka.html', form=form, organ=organ, color=color, nikname=nikname, action_users=action_users,  userof=userof)

# выход с профиля 
@main.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

# профиль
@main.route('/profile')
@login_required
def profile():
  return render_template('profile.html')
