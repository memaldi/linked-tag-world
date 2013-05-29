package eu.deustotech.internet.linkedtagworld.lib;

import android.app.Activity;
import android.content.Context;

import android.content.Intent;
import android.graphics.BitmapFactory;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ImageView;
import android.widget.TextView;
import eu.deustotech.internet.linkedtagworld.layout.Layout;
import eu.deustotech.internet.linkedtagworld.model.Widget;
import org.apache.http.HttpResponse;
import org.apache.http.client.HttpClient;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.impl.client.DefaultHttpClient;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;
import org.xml.sax.SAXException;

import com.hp.hpl.jena.rdf.model.Literal;
import com.hp.hpl.jena.rdf.model.Model;
import com.hp.hpl.jena.rdf.model.ModelFactory;
import com.hp.hpl.jena.rdf.model.NodeIterator;
import com.hp.hpl.jena.rdf.model.Property;
import com.hp.hpl.jena.rdf.model.RDFNode;
import com.hp.hpl.jena.rdf.model.Resource;
import com.hp.hpl.jena.vocabulary.RDF;

import java.io.IOException;
import java.io.InputStream;
import java.lang.reflect.Constructor;
import java.lang.reflect.InvocationTargetException;
import java.net.URL;
import java.util.*;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;

/**
 * Created by mikel on 21/05/13.
 */
public class LinkedTagWorld {

    private Context context;
    private Activity activity;
    private InputStream inputStream;

    private Map<String, String> uri2prefixMap = new HashMap<String, String>();
    private Map<String, String> prefix2uriMap = new HashMap<String, String>();

    private String className;

    private List<String> prefixedTypeList;
    
    private Model model;


    public LinkedTagWorld() {

    }

    public LinkedTagWorld(Context context, Activity activity, InputStream inputStream) {
        this.context = context;
        this.activity = activity;
        this.inputStream = inputStream;
    }

    public void renderData(String URI) throws ParserConfigurationException, IOException, SAXException, InstantiationException, IllegalAccessException, ClassNotFoundException {
        DocumentBuilderFactory docBuilderFactory = DocumentBuilderFactory.newInstance();
        DocumentBuilder docBuilder;

        docBuilder = docBuilderFactory.newDocumentBuilder();
        Document doc = docBuilder.parse(this.inputStream);

        fillPrefixesMaps(doc);

        this.model = setModel(URI);

        if (this.model.size() > 0) {
        
        	this.prefixedTypeList = getPrefixedTypeList(this.model);
	
	        Node pageNode = getPageNode(doc, this.prefixedTypeList);
	
	        Map<String, Widget> propertyMap = getPropertyMap(pageNode);
	
	        setLayout(propertyMap, doc);
        }

    }

    private void fillPrefixesMaps(Document doc) {
        NodeList prefixesList = doc.getElementsByTagName("prefixes");
        Node prefixes = prefixesList.item(0);

        this.prefix2uriMap.put("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#");
        this.uri2prefixMap.put("http://www.w3.org/1999/02/22-rdf-syntax-ns#", "rdf");

        NodeList prefixesChildren = prefixes.getChildNodes();

        for(int i = 0; i < prefixesChildren.getLength(); i++) {
            Node prefixItem = prefixesChildren.item(i);
            if (prefixItem.getNodeName().equals("prefixItem")) {
                NodeList prefixChildren = prefixItem.getChildNodes();
                String prefix = "";
                String uri = "";
                for(int j = 0; j < prefixChildren.getLength(); j++) {
                    if (prefixChildren.item(j).getNodeName().equals("prefix")) {
                        prefix = prefixChildren.item(j).getFirstChild().getNodeValue();
                    } else if (prefixChildren.item(j).getNodeName().equals("uri")) {
                        uri = prefixChildren.item(j).getFirstChild().getNodeValue();
                    }
                }
                this.prefix2uriMap.put(prefix, uri);
                this.uri2prefixMap.put(uri, prefix);
            }
        }
    }

    private Model setModel(String URI) throws IOException {
 	
        HttpClient client = new DefaultHttpClient();
        HttpGet request = new HttpGet(URI);
        request.addHeader("Accept", "application/rdf+xml");

        HttpResponse response = client.execute(request);
        InputStream inputStream = response.getEntity().getContent();

        Model model = ModelFactory.createDefaultModel();
        
        model.read(inputStream, null);
        
        return model;
        
    }
    
    private List<String> getPrefixedTypeList(Model model) {
    	List<String> typeList = new ArrayList<String>();
    	NodeIterator typeNodes = model.listObjectsOfProperty(RDF.type);
        
        while (typeNodes.hasNext()) {
        	RDFNode node = typeNodes.nextNode();
        	if(node.isResource()) {
        		Resource res = (Resource) node;
        		String type = res.getURI();
        		typeList.add(type);
        	}
        }
        
        List<String> prefixedTypeList = new ArrayList<String>();

        for (String type : typeList) {

            prefixedTypeList.add(String.format("%s:%s", this.uri2prefixMap.get(getPrefix(type)), type.split(getPrefix(type))[1]));
        }
        
        return prefixedTypeList;
    }

    private String getPrefix(String URI) {
        if (URI.contains("#")) {
            return URI.split("#")[0] + "#";
        } else {
            String [] splitURI = URI.split("/");
            String prefixURI = "";
            for (int i = 0; i < splitURI.length - 1; i++) {
                prefixURI += splitURI[i] + "/";
            }
            return prefixURI;
        }
    }

    private Node getPageNode(Document doc, List<String> prefixedTypeList) {
        NodeList pageItemList = doc.getElementsByTagName("pageItem");

        Node pageNode = null;
        for (int i = 0; i < pageItemList.getLength(); i++) {
            Node node = pageItemList.item(i);
            if (node.getNodeName().equals("pageItem")) {
                Element element = (Element) node;
                String classAttribute = element.getAttribute("type");
                if (prefixedTypeList.contains(classAttribute)) {
                    pageNode = node;
                    this.className = element.getAttribute("class");
                }
            }
        }
        return pageNode;
    }

    private Map<String, Widget> getPropertyMap(Node pageNode) {
        Map<String, Widget> propertyMap = new HashMap<String, Widget>();

        NodeList pageNodeChildren = pageNode.getChildNodes();
        for (int i = 0; i < pageNodeChildren.getLength(); i++) {
            Node node = pageNodeChildren.item(i);
            if (node.getNodeName().equals("items")) {
                NodeList childNodes = node.getChildNodes();
                for (int j = 0; j < childNodes.getLength(); j++) {
                    Node itemNode = childNodes.item(j);
                    NodeList itemNodeChildren = itemNode.getChildNodes();
                    if (itemNode.getNodeName().equals("item")) {

                        String property = "";
                        String id = itemNode.getAttributes().getNamedItem("id").getNodeValue();
                        boolean linkable = false;
                        if (itemNode.getAttributes().getNamedItem("linkable") != null) {
                            linkable = Boolean.valueOf(itemNode.getAttributes().getNamedItem("linkable").getNodeValue());
                        }

                        boolean main = false;
                        if (itemNode.getAttributes().getNamedItem("main") != null) {
                            main = Boolean.valueOf(itemNode.getAttributes().getNamedItem("main").getNodeValue());
                        }

                        Widget widget = new Widget(id, linkable, main);
                        for (int k = 0; k < itemNodeChildren.getLength(); k++) {
                            Node element = itemNodeChildren.item(k);
                            if (element.getNodeName().equals("property")) {
                                property = element.getFirstChild().getNodeValue();
                            }
                            if (!"".equals(property) && !"".equals(id)) {
                                propertyMap.put(property, widget);
                            }

                        }
                    }

                }
            }
        }
        return propertyMap;
    }

    private void setLayout(Map<String, Widget> propertyMap, Document doc) throws ClassNotFoundException, InstantiationException, IllegalAccessException, IOException {
        Class<Layout> layoutClass = (Class<Layout>) Class.forName(this.className);
        Layout layout = layoutClass.newInstance();

        this.activity.setContentView(layout.getLayout());

        Map<String, Integer> widgetMap = layout.getWidgets();

        for (String property : propertyMap.keySet()) {
        	String extendedProperty = this.prefix2uriMap.get(property.split(":")[0]) + property.split(":")[1];
        	
        	Property prop = this.model.getProperty(extendedProperty);
        	NodeIterator nodeIterator = this.model.listObjectsOfProperty(prop);
        	
        	while(nodeIterator.hasNext()) {
        		Widget widget = propertyMap.get(property);
        		String id = widget.getId();
        		RDFNode node = nodeIterator.next();
        		String object = "";
        		if (node.isLiteral()) {
        			Literal literalNode = (Literal) node;
        			object = literalNode.getString();
        		} else if (node.isResource()) {
        			Resource resNode = (Resource) node;
        			object = resNode.getURI();
        		}
        		int viewID = widgetMap.get(id);
        		Object view = this.activity.findViewById(viewID);
        		setView(object, view, null, widget, doc);
        	}
        }

        clearLayouts(widgetMap);

    }

    private void clearLayouts(Map<String, Integer> widgetMap) {
        for (String key : widgetMap.keySet()) {
            Integer widgetID = widgetMap.get(key);
            View view = this.activity.findViewById(widgetID);
            if (ViewGroup.class.isAssignableFrom(view.getClass())) {
                ViewGroup viewGroup = (ViewGroup) view;
                viewGroup.removeView(viewGroup.getChildAt(0));
            }
        }
    }

    private void setView(final String object, Object view, Object originalView, Widget widget, Document doc) throws IOException {
        if (view instanceof TextView) {
            TextView textView = (TextView) view;
            String template = "";
            if (originalView == null) {
                template = textView.getText().toString();
            } else {
                TextView originalTextView = (TextView) originalView;
                template = originalTextView.getText().toString();
            }
            String text = "";
            if (widget.isLinkable()) {

                String strObject = getMain(object, doc);

                try {
                    //Statement statement = main.get(0);
                    text = String.format(template, strObject);

                    textView.setOnClickListener( new View.OnClickListener() {
                        @Override
                        public void onClick(View view) {
                            Intent intent = new Intent(context.getApplicationContext(), activity.getClass());
                            intent.putExtra("getBoolean", false);
                            intent.putExtra("URI", object);

                            activity.startActivity(intent);
                        }
                    });
                } catch (NullPointerException e) {
                    text = String.format(template, object);
                }


            } else {
                text = String.format(template, object);
            }

            textView.setText(text);



        } else if (view instanceof ViewGroup) {
            ViewGroup layoutView = (ViewGroup) view;
            View child = layoutView.getChildAt(0);
            View childCopy = null;
            try {
                String childClassStr = child.getClass().getCanonicalName();
                System.out.println(childClassStr);
                Class<View> childClass = (Class<View>) Class.forName(child != null ? child.getClass().getCanonicalName() : null);

                Class[] constructorArgs = new Class[1];
                constructorArgs[0] = Context.class;
                Constructor<View> constructor = childClass.getDeclaredConstructor(constructorArgs);
                childCopy = constructor.newInstance(this.context);
            } catch (ClassNotFoundException e) {
                e.printStackTrace();
            } catch (NoSuchMethodException e) {
                e.printStackTrace();
            } catch (InvocationTargetException e) {
                e.printStackTrace();
            } catch (InstantiationException e) {
                e.printStackTrace();
            } catch (IllegalAccessException e) {
                e.printStackTrace();
            }
            setView(object, childCopy, child, widget, doc);
            childCopy.setVisibility(View.VISIBLE);
            childCopy.setLayoutParams(new ViewGroup.LayoutParams(new ViewGroup.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT)));
            layoutView.addView(childCopy);


        } else if (view instanceof ImageView) {
            ImageView imageView = (ImageView) view;
            try {
                imageView.setImageBitmap(BitmapFactory.decodeStream(new URL(object).openConnection().getInputStream()));
            } catch (IOException e) {
            	System.out.println("Error recovering image!");
                //e.printStackTrace();
            }

        }
    }

    private String getMain(String URI, Document doc) throws IOException {
        //Collection<Statement> statementCollection = setModel(URI);
    	Model uriModel = setModel(URI);
        if (uriModel.size() > 0) {
	        //Map<String, List<Statement>> predicateMap = getPredicateMap(statementCollection);
        	List<String> prefixedTypeList = getPrefixedTypeList(uriModel);
	        Node pageNode = getPageNode(doc, prefixedTypeList);
	        //Map<String, Widget> propertyMap = getPropertyMap(pageNode);
	        //Map<String, Widget> propertyMap = new HashMap<String, Widget>();
	
	        NodeList pageNodeChildren = pageNode.getChildNodes();
	        for (int i = 0; i < pageNodeChildren.getLength(); i++) {
	            Node node = pageNodeChildren.item(i);
	            if (node.getNodeName().equals("items")) {
	                NodeList childNodes = node.getChildNodes();
	                for (int j = 0; j < childNodes.getLength(); j++) {
	                    Node itemNode = childNodes.item(j);
	                    NodeList itemNodeChildren = itemNode.getChildNodes();
	                    if (itemNode.getNodeName().equals("item")) {
	
	                        String property = "";
	                        String id = itemNode.getAttributes().getNamedItem("id").getNodeValue();
	                        boolean linkable = false;
	                        if (itemNode.getAttributes().getNamedItem("linkable") != null) {
	                            linkable = Boolean.valueOf(itemNode.getAttributes().getNamedItem("linkable").getNodeValue());
	                        }
	
	                        boolean main = false;
	                        if (itemNode.getAttributes().getNamedItem("main") != null) {
	                            main = Boolean.valueOf(itemNode.getAttributes().getNamedItem("main").getNodeValue());
	                        }
	
	                        Widget widget = new Widget(id, linkable, main);
	                        for (int k = 0; k < itemNodeChildren.getLength(); k++) {
	                            Node element = itemNodeChildren.item(k);
	                            if (element.getNodeName().equals("property")) {
	                                property = element.getFirstChild().getNodeValue();
	                            }
	                            if (!"".equals(property) && !"".equals(id)) {
	                                //propertyMap.put(property, widget);
	                                if (widget.isMain()) {
	                                    String extendedProperty = prefix2uriMap.get(property.split(":")[0]) + property.split(":")[1];
	                                    //return predicateMap.get(extendedProperty);
	                                    
	                                    Property prop = uriModel.getProperty(extendedProperty);
	                                    NodeIterator nodeIterator = uriModel.listObjectsOfProperty(prop);
	                                    while(nodeIterator.hasNext()) {
	                                    	RDFNode rdfNode = nodeIterator.next();
	                                    	if (rdfNode.isLiteral()) {
	                                    		Literal literalNode = (Literal) rdfNode;
	                                    		return literalNode.getString();
	                                    	}
	                                    }
	                                }
	
	                            }
	
	                        }
	                    }
	
	                }
	            }
	        }
        }
        return null;
    }
}
