package {{ package }}.model;

import java.util.HashMap;
import java.util.Map;

import eu.deustotech.internet.linkedtagworld.layout.Layout;
import {{ package }}.R;

public class {{ model|title }} implements Layout {

	@Override
	public int getLayout() {
		return R.layout.{{ model }};
	}

	@Override
	public Map<String, Integer> getWidgets() {
		Map<String, Integer> widgetMap = new HashMap<String, Integer>();
		{% for prop in properties %}
		{% if prop.is_main %}
		widgetMap.put("{{ prop.id }}", R.id.{{ model }}_title);
		{% else %}
		widgetMap.put("{{ prop.id }}", R.id.{{ model }}_{{ prop.id }});
		{% endif %}
		{% endfor %}
		return widgetMap;
	}

}
