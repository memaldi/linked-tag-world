package eu.deustotech.internet.linkedtagworld.layout;

import java.util.Map;


/**
 * Layout interface to be overrided in the application by each entity in the model.
 * @author mikel
 */
public interface Layout {

	/**
	 * Returns the Android layout used to render the entity. The returned code is given from R.layout.layout_name
	 * @return the Android layout code used to render the entity	
	 */
    public int getLayout();
    
    /**
     * Returns the pairing between the widgets in the Android layout and properties specified in configuration file.
     * @return a Map containing the pairing between widgets and properties from configuration file
     */
    public Map<String, Integer> getWidgets();

}
