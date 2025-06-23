from django.http import HttpResponse
from django.template.loader import render_to_string
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import os
import base64
from io import BytesIO
from django.shortcuts import render
from django.conf import settings
from collections import defaultdict


def index(request):
    t = render_to_string('designer/index.html')
    return HttpResponse(t)


def get_exchange_rate(currency, date):
    """Примерная функция перевода курса валют"""
    rates = {
        'USD': 75.0,
        'EUR': 85.0,
        'KZT': 0.18,
    }
    return rates.get(currency.upper(), 1.0)


def general_statistics(request):
    csv_path = os.path.join(settings.BASE_DIR, 'designer', 'data', 'IT_vacancies_full.csv')
    if not os.path.exists(csv_path):
        return HttpResponse("Файл данных не найден", status=404)

    try:
        df = pd.read_csv(csv_path, parse_dates=['Published at'])

        df['Salary_avg'] = df[['From', 'To']].mean(axis=1)
        df['Salary_avg'] = df['Salary_avg'].fillna(df['Salary'])

        df = df[df['Salary_avg'] <= 10_000_000]
        df['Currency'] = df.get('Currency', 'RUB')
        df['Salary_RUB'] = df.apply(
            lambda row: row['Salary_avg'] * get_exchange_rate(row.get('Currency', 'RUB'), row['Published at']),
            axis=1
        )
        df['Year'] = df['Published at'].dt.year

        salary_by_year = df.groupby('Year')['Salary_RUB'].mean().reset_index()
        count_by_year = df['Year'].value_counts().sort_index().reset_index()
        count_by_year.columns = ['Year', 'Count']
        top_cities_salary = df.groupby('Area')['Salary_RUB'].mean().sort_values(ascending=False).head(10).reset_index()
        top_cities_count = df['Area'].value_counts(normalize=True).head(10).reset_index()
        top_cities_count.columns = ['Area', 'Share']

        df['Keys'] = df['Keys'].fillna('')
        df['Skills'] = df['Keys'].str.split(',').apply(lambda lst: [skill.strip() for skill in lst if skill.strip()])

        skills_by_year = defaultdict(lambda: defaultdict(int))
        for _, row in df.iterrows():
            for skill in row['Skills']:
                skills_by_year[row['Year']][skill] += 1

        top_skills_per_year = {
            year: sorted(skills.items(), key=lambda x: -x[1])[:20]
            for year, skills in skills_by_year.items()
        }

        def plot_to_base64(fig):
            buffer = BytesIO()
            fig.savefig(buffer, format='png', bbox_inches='tight', facecolor=fig.get_facecolor())
            plt.close(fig)
            return base64.b64encode(buffer.getvalue()).decode('utf-8')

        # Бирюзовая палитра
        turquoise_palette = ['#00bcd4', '#0097a7', '#b2ebf2', '#006064', '#4dd0e1', '#26c6da', '#80deea', '#00acc1', '#00838f', '#004d40']

        # 1. Динамика зарплат
        fig1, ax1 = plt.subplots(figsize=(10, 5))
        sns.lineplot(data=salary_by_year, x='Year', y='Salary_RUB', marker='o', color='#00bcd4', ax=ax1)
        ax1.set_title('Средняя зарплата по годам', color='#006064')
        ax1.tick_params(colors='#006064')
        ax1.grid(True, linestyle='--', color='#80deea')
        salary_plot = plot_to_base64(fig1)

        # 2. Количество вакансий
        fig2, ax2 = plt.subplots(figsize=(10, 5))
        sns.barplot(data=count_by_year, x='Year', y='Count', color='#00bcd4', ax=ax2)
        ax2.set_title('Количество вакансий по годам', color='#006064')
        ax2.tick_params(colors='#006064')
        ax2.grid(True, linestyle='--', color='#80deea')
        count_plot = plot_to_base64(fig2)

        # 3. Зарплаты по городам
        fig3, ax3 = plt.subplots(figsize=(12, 6))
        sns.barplot(data=top_cities_salary, x='Salary_RUB', y='Area', palette=turquoise_palette, ax=ax3)
        ax3.set_title('Зарплаты по городам (ТОП-10)', color='#006064')
        ax3.tick_params(colors='#006064')
        ax3.grid(True, axis='x', linestyle='--', color='#80deea')
        cities_salary_plot = plot_to_base64(fig3)

        # 4. Доля вакансий по городам
        fig4, ax4 = plt.subplots(figsize=(10, 6))
        ax4.pie(top_cities_count['Share'], labels=top_cities_count['Area'], autopct='%1.1f%%',
                colors=turquoise_palette, textprops={'color': '#006064'})
        ax4.set_title('Доля вакансий по городам (ТОП-10)', color='#006064')
        cities_count_plot = plot_to_base64(fig4)

        context = {
            'salary_by_year': salary_by_year.to_dict('records'),
            'count_by_year': count_by_year.to_dict('records'),
            'top_cities_salary': top_cities_salary.to_dict('records'),
            'top_cities_count': top_cities_count.to_dict('records'),
            'top_skills_per_year': top_skills_per_year,
            'salary_plot': salary_plot,
            'count_plot': count_plot,
            'cities_salary_plot': cities_salary_plot,
            'cities_count_plot': cities_count_plot,
        }

        return render(request, 'designer/general_statistics.html', context)

    except Exception as e:
        return HttpResponse(f"Ошибка обработки данных: {str(e)}", status=500)


def demand(request):
    try:
        # Путь к файлу
        csv_path = os.path.join(settings.BASE_DIR, 'designer', 'data', 'IT_vacancies_full.csv')

        if not os.path.exists(csv_path):
            return HttpResponse(f"Файл не найден по пути: {csv_path}", status=404)

        # Загрузка данных
        df = pd.read_csv(csv_path, usecols=['Name', 'From', 'To', 'Published at'])

        # Фильтрация по профессии
        profession = 'UX/UI дизайнер'
        df = df[df['Name'].str.contains(profession, case=False, na=False)].copy()

        # Извлечение года
        df['year'] = pd.to_datetime(df['Published at']).dt.year

        # 1. Динамика зарплат
        # Конвертация зарплат в рубли
        df['Salary_RUB'] = df.apply(lambda row:
                                    (row['From'] + row['To']) / 2 if not pd.isna(row['From']) and not pd.isna(row['To'])
                                    else row['From'] if not pd.isna(row['From'])
                                    else row['To'] if not pd.isna(row['To'])
                                    else None, axis=1)

        # Удаляем строки с некорректными зарплатами
        df_salary = df[df['Salary_RUB'].notna() & (df['Salary_RUB'] < 10_000_000)]

        salary_dynamics = (
            df_salary.groupby('year')['Salary_RUB']
            .mean()
            .round(2)
            .reset_index()
        )

        # 2. Динамика количества вакансий
        vacancies_dynamics = (
            df['year'].value_counts()
            .sort_index()
            .reset_index()
        )
        vacancies_dynamics.columns = ['year', 'count']

        # Подготовка данных для шаблона
        context = {
            'profession': profession,
            'salary_dynamics': salary_dynamics.to_dict('records'),
            'vacancies_dynamics': vacancies_dynamics.to_dict('records'),
            'salary_labels': salary_dynamics['year'].tolist(),
            'salary_data': salary_dynamics['Salary_RUB'].tolist(),
            'vacancy_labels': vacancies_dynamics['year'].tolist(),
            'vacancy_data': vacancies_dynamics['count'].tolist(),
        }

        return render(request, 'designer/demand.html', context)

    except Exception as e:
        return HttpResponse(f"Произошла ошибка: {str(e)}", status=500)


def geography(request):
    try:
        # Путь к файлу
        csv_path = os.path.join(settings.BASE_DIR, 'designer', 'data', 'IT_vacancies_full.csv')

        if not os.path.exists(csv_path):
            return HttpResponse(f"Файл не найден по пути: {csv_path}", status=404)

        # Загрузка нужных колонок
        df = pd.read_csv(csv_path, usecols=['Name', 'Area', 'From', 'To', 'Published at'])

        # Фильтрация по профессии
        profession = 'UX/UI дизайнер'
        df = df[df['Name'].str.contains(profession, case=False, na=False)].copy()

        # Конвертация зарплат в рубли (аналогично динамике зарплат)
        df['Salary_RUB'] = df.apply(lambda row:
                                    (row['From'] + row['To']) / 2 if not pd.isna(row['From']) and not pd.isna(row['To'])
                                    else row['From'] if not pd.isna(row['From'])
                                    else row['To'] if not pd.isna(row['To'])
                                    else None, axis=1)

        # Удаляем строки с некорректными зарплатами
        df = df[df['Salary_RUB'].notna() & (df['Salary_RUB'] < 10_000_000)]

        # 1. Уровень зарплат по городам (топ-10)
        salary_by_city = (
            df.groupby('Area')['Salary_RUB']
            .mean()
            .sort_values(ascending=False)
            .head(10)
            .reset_index()
        )

        # 2. Доля вакансий по городам (топ-10)
        vacancies_by_city = (
            df['Area'].value_counts(normalize=True)
            .head(10)
            .mul(100)
            .round(2)
            .reset_index()
        )
        vacancies_by_city.columns = ['City', 'Percentage']

        # Подготовка данных для шаблона
        context = {
            'profession': profession,
            'salary_by_city': salary_by_city.to_dict('records'),
            'vacancies_by_city': vacancies_by_city.to_dict('records'),
            # Добавляем данные для графиков в виде списков
            'salary_labels': salary_by_city['Area'].tolist(),
            'salary_data': salary_by_city['Salary_RUB'].tolist(),
            'vacancy_labels': vacancies_by_city['City'].tolist(),
            'vacancy_data': vacancies_by_city['Percentage'].tolist(),
        }

        return render(request, 'designer/geography.html', context)

    except Exception as e:
        return HttpResponse(f"Произошла ошибка: {str(e)}", status=500)

        return render(request, 'designer/geography.html', context)

    except Exception as e:
        return HttpResponse(f"Произошла ошибка: {str(e)}", status=500)


def skills(request):
    try:
        # Получаем абсолютный путь к файлу
        csv_path = os.path.join(settings.BASE_DIR, 'designer', 'data', 'IT_vacancies_full.csv')

        # Проверяем существование файла
        if not os.path.exists(csv_path):
            return HttpResponse(f"Файл не найден по пути: {csv_path}", status=404)

        # Загрузка данных с правильными названиями столбцов
        df = pd.read_csv(csv_path, usecols=['Name', 'Published at', 'Keys'])

        # Определяем профессию
        profession = request.GET.get('profession', 'UX/UI дизайнер')

        # Фильтрация по профессии
        profession_df = df[df['Name'].str.contains(profession, case=False, na=False)].copy()

        # Извлечение года из даты
        profession_df['year'] = pd.to_datetime(profession_df['Published at']).dt.year

        # Словарь для хранения результатов
        skills_dict = defaultdict(lambda: defaultdict(int))

        # Обработка каждой строки
        for _, row in profession_df.iterrows():
            year = row['year']
            skills = row['Keys']

            if pd.notna(skills):
                # Удаляем квадратные скобки и кавычки, разделяем по запятым
                skills_clean = str(skills).replace('[', '').replace(']', '').replace("'", "")
                for skill in [s.strip() for s in skills_clean.split(',') if s.strip()]:
                    skills_dict[year][skill] += 1

        # Подготовка данных для шаблона
        result = {}
        for year in sorted(skills_dict.keys()):
            # Сортируем навыки по частоте и берем топ-20
            top_skills = sorted(skills_dict[year].items(), key=lambda x: x[1], reverse=True)[:20]
            # Преобразуем в список словарей для удобного вывода
            result[year] = [{'skill': skill, 'count': count} for skill, count in top_skills]

        context = {
            'profession': profession,
            'skills_by_year': result
        }
        return render(request, 'designer/skills.html', context)

    except Exception as e:
        return HttpResponse(f"Произошла ошибка: {str(e)}", status=500)

    except Exception as e:
        return HttpResponse(f"Произошла ошибка: {str(e)}", status=500)
