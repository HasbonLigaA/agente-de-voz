"""La Liga Ama Salvar Vidas — quiénes somos e identidad institucional.

Fuente: https://laligaamasalvarvidas.org.co/nuestra-institucion
"""

from __future__ import annotations

from backend.knowledge.plan_liga import PLAN_LIGA

INSTITUTION_SOURCE_URL = "https://laligaamasalvarvidas.org.co/nuestra-institucion"

INSTITUTION: dict = {
    "nombre": "La Liga Ama Salvar Vidas",
    "tipo": "Entidad privada sin ánimo de lucro",
    "sede": "Pereira, Risaralda, Colombia",
    "historia_resumen": (
        "El 12 de abril de 1976 nació en Pereira, impulsada por el espíritu cívico de la "
        "sociedad y liderada por Bernardo Ángel Marulanda junto a un grupo de voluntarias, "
        "con el fin de beneficiar a la población de manera desinteresada. "
        "Hoy es una institución reconocida en el departamento, la región y el país, con un "
        "portafolio de servicios de salud en crecimiento y proyección al Eje Cafetero."
    ),
    "vision": (
        "Ser la entidad líder en el diagnóstico y tratamiento, con soluciones integrales de "
        "salud, brindando la mejor experiencia a los pacientes y sus familias."
    ),
    "mision": (
        "Brindar bienestar y salud a los pacientes, sus familias y la comunidad, con amor y "
        "pasión, apoyados por un voluntariado comprometido, con atención humanizada, de "
        "calidad, con alta tecnología y responsabilidad social, integrando la educación y la "
        "investigación."
    ),
    "valores": {
        "Respeto": "Honrar los derechos y la dignidad de usuarios, colaboradores e instituciones.",
        "Transparencia": "Comportarse con honestidad y coherencia.",
        "Equidad": "Bienestar según necesidades, sin discriminar por diferencias culturales, sociales o de género.",
        "Trabajo en Equipo": "Participación activa hacia un objetivo común.",
        "Empatía": "Entender y acompañar sentimientos y emociones de las personas.",
        "Responsabilidad": "Compromiso con las tareas y resultados concretos.",
    },
    "politica_calidad_resumen": (
        "Atención integral del paciente con énfasis en cáncer y otras enfermedades, desde la "
        "prevención, con altos estándares de calidad, personal competente, acciones seguras "
        "y atención humanizada, mejora continua y sostenibilidad para la comunidad."
    ),
    "que_hace": (
        "Presta servicios de salud con enfoque integral: diagnóstico, tratamiento, prevención "
        "y acompañamiento a pacientes y familias, con voluntariado, tecnología y "
        "responsabilidad social."
    ),
    # Textos breves para respuesta por voz
    "pitch_voz": (
        "La Liga Ama Salvar Vidas es una fundación sin ánimo de lucro en Pereira, activa desde 1976. "
        "Brinda servicios de salud integrales: diagnóstico, tratamiento, prevención y "
        "acompañamiento a pacientes y familias."
    ),
    "para_que_sirve_voz": (
        "Sirve para ofrecer bienestar y salud a la comunidad, con atención humanizada, "
        "tecnología y apoyo de voluntariado, desde la prevención hasta el tratamiento."
    ),
    "historia_voz": (
        "Fundada el 12 de abril de 1976 en Pereira por Bernardo Ángel Marulanda y un grupo de "
        "voluntarias, para servir a la población sin ánimo de lucro."
    ),
    "mision_voz": (
        "Brindar bienestar y salud con amor, atención humanizada, tecnología y voluntariado "
        "comprometido, integrando educación e investigación."
    ),
    "vision_voz": (
        "Ser líder en diagnóstico y tratamiento, con soluciones integrales de salud y la mejor "
        "experiencia para pacientes y familias."
    ),
    "valores_voz": "Respeto, transparencia, equidad, trabajo en equipo, empatía y responsabilidad.",
}

CONTACTO = {
    **PLAN_LIGA["contacto"],
    "nombre_institucion": INSTITUTION["nombre"],
    "ciudad": INSTITUTION["sede"],
    "pbx_administrativo": "+57 606 3341513",
    "correo_citas": "citasmedicas@laliga.org.co",
    "notificaciones_judiciales": "notificacionesjudiciales@laliga.org.co",
}
