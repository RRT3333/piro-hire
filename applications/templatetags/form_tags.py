from django import template

register = template.Library()

@register.filter(name='addclass')
def addclass(value, arg):
    css_classes = value.field.widget.attrs.get('class', '').split()
    if arg not in css_classes:
        css_classes.append(arg)
    return value.as_widget(attrs={'class': ' '.join(css_classes)}) 