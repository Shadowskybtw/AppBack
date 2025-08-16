# 📱 Настройка WebApp для фронтенда

## 🎯 **Проблема**
WebApp открывается только у вас, а у других пользователей не работает. Это происходит из-за:
1. **CORS ограничений** - бэкенд не разрешает запросы с других доменов
2. **Проблем с сохранением данных** - пользователи не сохраняются в БД
3. **Неправильной инициализации** - WebApp не проверяет существование пользователя

## ✅ **Решение**

### **1. Бэкенд исправлен**
- ✅ **CORS разрешен для всех доменов** - `allow_origins=["*"]`
- ✅ **Пользователи сохраняются в SQLite** - мини БД работает
- ✅ **Новый эндпоинт** `/api/webapp/init/{tg_id}` для инициализации

### **2. Фронтенд нужно обновить**

## 🔧 **Изменения во фронтенде**

### **Добавить проверку пользователя при загрузке**

```javascript
// В компоненте App.js или главном компоненте
useEffect(() => {
  const initWebApp = async () => {
    try {
      // Получаем Telegram ID из WebApp
      const tgId = window.Telegram.WebApp.initDataUnsafe?.user?.id;
      
      if (tgId) {
        // Проверяем существование пользователя
        const response = await fetch(`/api/webapp/init/${tgId}`);
        const data = await response.json();
        
        if (data.userExists) {
          // Пользователь существует - показываем основной интерфейс
          setUser(data.user);
          setRegistered(true);
        } else {
          // Пользователь не найден - показываем форму регистрации
          setRegistered(false);
        }
      }
    } catch (error) {
      console.error('Error initializing WebApp:', error);
      // Показываем форму регистрации по умолчанию
      setRegistered(false);
    }
  };

  initWebApp();
}, []);
```

### **Исправить регистрацию пользователя**

```javascript
const handleRegistration = async (formData) => {
  try {
    const response = await fetch('/api/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        tg_id: window.Telegram.WebApp.initDataUnsafe?.user?.id,
        firstName: formData.firstName,
        lastName: formData.lastName,
        phone: formData.phone,
        username: window.Telegram.WebApp.initDataUnsafe?.user?.username
      }),
    });

    if (response.ok) {
      const data = await response.json();
      setUser(data.user);
      setRegistered(true);
      // Сохраняем в localStorage для персистентности
      localStorage.setItem('user', JSON.stringify(data.user));
    }
  } catch (error) {
    console.error('Registration error:', error);
  }
};
```

### **Добавить персистентность данных**

```javascript
// При загрузке компонента
useEffect(() => {
  // Проверяем localStorage
  const savedUser = localStorage.getItem('user');
  if (savedUser) {
    const user = JSON.parse(savedUser);
    setUser(user);
    setRegistered(true);
  }
}, []);
```

## 🚀 **Полный алгоритм работы WebApp**

### **1. Загрузка WebApp**
```
WebApp открывается → Получаем Telegram ID → Проверяем пользователя в БД
```

### **2. Проверка пользователя**
```
Если пользователь найден → Показываем основной интерфейс
Если пользователь не найден → Показываем форму регистрации
```

### **3. Регистрация**
```
Заполнение формы → Отправка на /api/register → Сохранение в БД → Сохранение в localStorage
```

### **4. Повторное открытие**
```
WebApp открывается → Проверяем localStorage → Если есть пользователь → Показываем основной интерфейс
```

## 📝 **Код для копирования**

### **App.js (основной компонент)**
```javascript
import React, { useState, useEffect } from 'react';
import RegistrationForm from './components/RegistrationForm';
import MainInterface from './components/MainInterface';

function App() {
  const [user, setUser] = useState(null);
  const [registered, setRegistered] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initWebApp = async () => {
      try {
        // Инициализируем Telegram WebApp
        window.Telegram.WebApp.ready();
        window.Telegram.WebApp.expand();
        
        const tgId = window.Telegram.WebApp.initDataUnsafe?.user?.id;
        
        if (tgId) {
          // Проверяем существование пользователя
          const response = await fetch(`/api/webapp/init/${tgId}`);
          const data = await response.json();
          
          if (data.userExists) {
            setUser(data.user);
            setRegistered(true);
          } else {
            // Проверяем localStorage
            const savedUser = localStorage.getItem('user');
            if (savedUser) {
              const user = JSON.parse(savedUser);
              setUser(user);
              setRegistered(true);
            } else {
              setRegistered(false);
            }
          }
        }
      } catch (error) {
        console.error('Error initializing WebApp:', error);
        // Проверяем localStorage как fallback
        const savedUser = localStorage.getItem('user');
        if (savedUser) {
          const user = JSON.parse(savedUser);
          setUser(user);
          setRegistered(true);
        } else {
          setRegistered(false);
        }
      } finally {
        setLoading(false);
      }
    };

    initWebApp();
  }, []);

  const handleRegistration = async (formData) => {
    try {
      const response = await fetch('/api/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          tg_id: window.Telegram.WebApp.initDataUnsafe?.user?.id,
          firstName: formData.firstName,
          lastName: formData.lastName,
          phone: formData.phone,
          username: window.Telegram.WebApp.initDataUnsafe?.user?.username
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setUser(data.user);
        setRegistered(true);
        // Сохраняем в localStorage
        localStorage.setItem('user', JSON.stringify(data.user));
      }
    } catch (error) {
      console.error('Registration error:', error);
    }
  };

  if (loading) {
    return <div>Загрузка...</div>;
  }

  return (
    <div className="App">
      {registered ? (
        <MainInterface user={user} />
      ) : (
        <RegistrationForm onRegister={handleRegistration} />
      )}
    </div>
  );
}

export default App;
```

## 🔍 **Тестирование**

### **1. Локальное тестирование**
```bash
# Запустить бэкенд
make run

# Открыть фронтенд
# Отправить /start боту
# Проверить открытие WebApp
```

### **2. Проверка в браузере**
- Откройте DevTools → Console
- Проверьте запросы к API
- Убедитесь, что пользователь сохраняется

### **3. Проверка БД**
```bash
# Проверить SQLite БД
sqlite3 db.sqlite3
SELECT * FROM users;
SELECT * FROM stocks;
```

## 🚨 **Возможные проблемы**

### **1. CORS ошибки**
- Убедитесь, что бэкенд запущен
- Проверьте `allow_origins=["*"]` в main.py

### **2. Пользователь не сохраняется**
- Проверьте логи бэкенда
- Убедитесь, что БД создана
- Проверьте права на запись в файл

### **3. WebApp не открывается**
- Проверьте токен бота
- Убедитесь, что фронтенд доступен
- Проверьте настройки в @BotFather

## ✅ **Результат**

После внесения изменений:
- ✅ **WebApp будет открываться у всех пользователей**
- ✅ **Данные будут сохраняться в SQLite БД**
- ✅ **Регистрация не будет повторяться**
- ✅ **Данные будут персистентными**

---

**🎉 Теперь WebApp будет работать корректно для всех пользователей!**
